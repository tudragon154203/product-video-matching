# Sprint 2 – eBay Browse Search (Specs-First, Minimal Code)

> Purpose: Replace the mock eBay collector with a **real Browse keyword search** path that **keeps downstream unchanged**. This canvas prioritizes **requirements and specs**; code is kept to the **absolute minimum** so an implementer can fill in details safely.

---

## 1) Goals & Non‑Goals

### Goals

- Implement **keyword search** via **eBay Browse API** (`/buy/browse/v1/item_summary/search`).
- Enforce **Sprint‑1 business rules** as defaults (see §4 Filters & Defaults).
- Provide a **clean collector interface** used by all collectors.
- Implement a \*\*real \*\*`` that:
  - Queries one or more marketplaces;
  - **Deduplicates by EPID** (fallback `itemId`) and **keeps the lowest total** (price + shipping);
  - Maps eBay fields to our **internal product shape**;
  - Passes images downstream (existing image pipeline handles resize \~400px & events).
- Centralize **timeout/retry/backoff** knobs in config; the client imports them.

### Non‑Goals

- No schema changes to DB or events.
- No affiliate/EPN work.
- No conversion to a unified currency (keep currency as returned).

---

## 2) High‑Level Architecture

```
Event → DropshipProductFinderService → ProductCollectionManager
      → EbayProductCollector (real)
          ↳ EbayBrowseApiClient (auth via eBayAuthService)
              ↳ eBay Browse API (search)
      → ImageStorageManager → DB + image downloads + events
```

- **Auth**: Reuse existing `eBayAuthService` + Redis token cache.
- **Isolation**: Business defaults live in **collector**; transport concerns in the **client**.

---

## 3) Internal Product Shape (as used today)

For each product (unchanged downstream):

- `id` (string) – e.g., eBay `itemId` (fallback a generated id if missing);
- `title` (string);
- `brand` (string | null) – from `brand` or `manufacturer` if present;
- `url` (string) – prefer `itemWebUrl` then `itemAffiliateWebUrl`;
- `images` (string[]) – up to 6 URLs (primary + additional);
- `marketplace` ("us" | "de" | "au" | etc.);
- `price` (string/number-like) – keep the value returned by Browse;
- `currency` (string) – the currency code from Browse.

---

## 4) Filters & Defaults (Sprint‑1 carry‑overs)

Applied for every search unless overridden by future business logic:

- **Buying option**: `FIXED_PRICE` only
- **Returns accepted**: `true`
- **Ship‑to**: `deliveryCountry=US`
- **Shipping cost**: `maxDeliveryCost=0` (free shipping)
- **Price range**: `price:[10..40]`
- **Currency**: `priceCurrency=USD`
- **Condition**: `conditionIds:{1000}` (= NEW)
- **Field groups**: `fieldgroups=EXTENDED` (to access shipping options, etc.)

> These are encoded in the client as a **single filter string** and appended to `filter`.

---

## 5) Pagination & Limits

- Use `limit=min(50, top_k)` per marketplace request (adjustable later).
- If less than `top_k` items are returned, **accept fewer** and log.
- Only first page for Sprint 2 (keep simple); pagination can be extended if needed.

---

## 6) Deduplication & Selection

- Primary key for dedup: ``; fallback ``.
- Selection rule per duplicate group: keep item with **lowest \*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\***``, where
  - `total = price + shippingCost` (from EXTENDED shipping options);
  - If shipping missing, compare by `price` only;
  - Tie‑break: stable order (no further tie‑break needed in Sprint 2).

---

## 7) Images

- Collect **primary** (`image.imageUrl`) and **additional** (`additionalImages[].imageUrl`).
- Cap at **6** images per product to limit storage & bandwidth.
- **Do not fail** the product when some images fail to download (handled downstream).

---

## 8) Error Handling & Resiliency

- **401**: force a single token refresh and retry once.
- **429 / 5xx**: short exponential backoff and retry (configurable).
- **Network errors**: retry per backoff; log and return empty on exhaustion.
- Always return a **well‑formed list** (possibly empty). No exceptions leak to the handler.

---

## 9) Configuration (centralized)

In `config_loader.py` add these tunables (env‑override allowed):

```python
# config_loader.py (append)
TIMEOUT_SECS_BROWSE = float(os.getenv("BROWSE_TIMEOUT_SECS", 30.0))
MAX_RETRIES_BROWSE = int(os.getenv("BROWSE_MAX_RETRIES", 2))
BACKOFF_BASE_BROWSE = float(os.getenv("BROWSE_BACKOFF_BASE", 1.5))

@property
def EBAY_BROWSE_BASE(self) -> str:
    """Get the appropriate Browse API base URL based on environment"""
    if self.EBAY_ENVIRONMENT == "production":
        return "https://api.ebay.com/buy/browse/v1"
    return "https://api.sandbox.ebay.com/buy/browse/v1"
```



---

## 10) Minimal Code (only interfaces & skeletons)

### 10.1 Collector Interface

```python
# collectors/interface.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class IProductCollector(ABC):
    @abstractmethod
    async def collect_products(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Collect products for a keyword query; return normalized dicts."""
        raise NotImplementedError
```

### 10.2 Browse Client (signature + constants import)

```python
# services/ebay_browse_api_client.py
from typing import Dict, Any, Optional
from config_loader import TIMEOUT_SECS_BROWSE, MAX_RETRIES_BROWSE, BACKOFF_BASE_BROWSE

FILTER = (
    "buyingOptions:{FIXED_PRICE},"
    "returnsAccepted:true,"
    "deliveryCountry:US,"
    "maxDeliveryCost:0,"
    "price:[10..40],"
    "priceCurrency:USD,"
    "conditionIds:{1000}"
)

class EbayBrowseApiClient:
    def __init__(self, auth_service, marketplace_id: str, base_url: str):
        self.auth = auth_service
        self.marketplace_id = marketplace_id
        self.base_url = base_url.rstrip("/")

    async def search(self, q: str, limit: int, offset: int = 0,
                     extra_filter: Optional[str] = None) -> Dict[str, Any]:
        """Perform keyword search with fixed Sprint‑1 filters and EXTENDED fieldgroups."""
        ...  # implement per specs §4, §8 using the imported tunables
```

### 10.3 Real eBay Collector (skeleton only)

```python
# collectors/ebay_product_collector.py
from typing import List, Dict, Any, Optional
from collections import defaultdict
from collectors.interface import IProductCollector
from services.ebay_browse_api_client import EbayBrowseApiClient
from config_loader import config, get_ebay_browse_base

class EbayProductCollector(IProductCollector):
    def __init__(self, auth_service, marketplaces: Optional[List[str]] = None):
        self.auth = auth_service
        self.marketplaces = (marketplaces or config.EBAY_MARKETPLACES.split(","))
        self.base_url = get_ebay_browse_base()

    async def collect_products(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        # 1) Guard clauses; 2) Request per marketplace; 3) Dedup by EPID→lowest total; 4) Map to internal shape
        ...  # implement per specs §5–§7
```

> Intentionally minimal: the implementer fills in HTTP calls, retry, mapping, and dedup logic following the specs above.

---

## 11) Logging & Metrics

- Log per request: query, marketplace, limit, status, latency, retries.
- Counters: 401 refresh count, 429/5xx retry count, empty result rate, dedup savings.
- Emit warnings when returned count < `top_k` (likely sandbox scarcity).

---

## 12) Testing & Acceptance

### Unit

- Client: ensures `fieldgroups=EXTENDED` and the fixed filter are present; verifies retry on 401; backoff on 429/5xx.
- Collector: dedup by EPID (fallback `itemId`); lowest total selection; image list capped at 6; mapping yields required fields.

### Integration (Sandbox)

- Query: `"iphone"` with `top_k=5` returns ≥1 normalized product satisfying defaults.
- Images flow into existing pipeline; events are emitted as usual.

### Acceptance Checklist

- ✅ Defaults applied (see §4) and visible in request
- ✅ No duplicate EPIDs in the final list
- ✅ Lowest total selected among duplicates
- ✅ No downstream contract changes

---

##

