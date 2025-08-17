# Sprint 8 – eBay Integration for Dropship Product Finder

> Goal: Integrate eBay **Browse API** into the `dropship-product-finder` service according to the agreed business constraints. Maintain the image‑first pipeline (download images → emit `products.image.ready`) without requiring changes to downstream services.

> **Note:** This implementation will initially run in the **eBay Sandbox** environment. The `.env` file for the `dropship-product-finder` service will include `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET`. These will be read via `config_loader` and used within the application. The service should obtain a fresh `access_token` at startup by calling **Step 1 – Get access token**: send a POST request to `/identity/v1/oauth2/token` with Basic Auth `<CLIENT_ID>:<CLIENT_SECRET>` and receive an `access_token` (usually valid for \~2 hours). The `fieldgroups=EXTENDED` parameter should be included in Browse API requests to retrieve extended data. **Caution:** If the API is overused or exceeds the burst rate limit (e.g., 5–10 requests/second depending on account), eBay may temporarily suspend the API key.

---

## 1) Scope & Assumptions

- **Supported marketplaces:** `EBAY_US` (default), plus `EBAY_DE`, `EBAY_AU` via config.
- **Search scope:** entire marketplace (no category restriction).
- **Sort:** default *Best Match* from eBay (no override).
- **Ship to:** US.
- **Free shipping:** required.
- **Price:** \$10 ≤ **price** < \$40 (USD).
- **Condition:** **NEW** (conditionId `1000`).
- **Buying option:** **FIXED\_PRICE** only.
- **Deduplication:** by **EPID** (if duplicate, keep the one with the lowest **total price** = item price + shipping).
- **Variants:** do not group; each `itemId` is a separate product.
- **Images:** retrieve **all** (primary + additional). If one image fails, continue downloading others.
- **Image resize:** longest side ≈ **400px** (keep aspect ratio) before saving locally & emitting event.
- **Image storage:** in `product_images` table, store both **local image path** and **original image URL** (`image_url_remote`). Delete any images older than **7 days**; they can be re-fetched from the remote URL if needed.
- **top\_ebay:** value comes from the `main-api` service request payload.
- **Retry:** 3 times on HTTP errors; skip item if still failing.
- **Affiliate/EPN:** not used.
- **Enrich:** do not call `getItem` if search already provides price/shipping info.
- **Database:** **Breaking change**
  - Drop the existing `products` table and re‑initialize. Add new columns:
    - `marketplace` – enum (`us`, `de`, `au`).
    - `price` – string including currency (e.g., `$20`, `€3`, `5 AUD`).
  - In `product_images` table: `image_url_remote` – string storing the original image URL.

---

## 2) Integration with Existing Pipeline

- **Consumer input:** listens to `products.collect.request`. Takes `queries.en` and `top_ebay` from payload.
- **eBay Collector:** calls Browse Search with filters in §3, merges results from configured marketplaces, deduplicates by EPID, downloads & resizes images.
- **Producer output:** emits `products.image.ready` for each image.
- **Downstream:** No changes to other services.

---

## 3) eBay Collector Design

**Related eBay Docs:**

- [eBay Buy APIs Overview](https://developer.ebay.com/api-docs/buy/overview.html)
- [Browse API v1](https://developer.ebay.com/api-docs/buy/browse/overview.html)
- [Browse API – item\_summary/search](https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search)
- [Identity (OAuth) API](https://developer.ebay.com/api-docs/commerce/identity/overview.html)

### 3.1 Access Token Retrieval

- **POST** `/identity/v1/oauth2/token` with Basic Auth `<CLIENT_ID>:<CLIENT_SECRET>`.
- Sandbox: `https://api.sandbox.ebay.com`.
- Body: `grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope`.
- Retrieve token at service startup; refresh before expiry or on `401`.

### 3.2 Browse Search

- **GET** `/buy/browse/v1/item_summary/search` with `fieldgroups=EXTENDED`.
- Headers: Bearer token, `X-EBAY-C-MARKETPLACE-ID`.
- Filters:

```
buyingOptions:{FIXED_PRICE},returnsAccepted:true,deliveryCountry:US,maxDeliveryCost:0,price:[10..40],priceCurrency:USD,conditionIds:{1000}
```

### 3.3 Deduplication & Images

- Deduplicate by `epid` (fallback `itemId`).
- Download all images, resize to \~400px, retry failed downloads ×3.
- Store both local and remote image URLs in `product_images`; schedule cleanup for images older than 7 days.

---

## 4) Config & Secrets

**.env**

```env
EBAY_CLIENT_ID=your_app_id
EBAY_CLIENT_SECRET=your_app_secret
EBAY_MARKETPLACES=EBAY_US,EBAY_DE,EBAY_AU
```

**.env.example**

```env
EBAY_CLIENT_ID=example_client_id
EBAY_CLIENT_SECRET=example_client_secret
EBAY_MARKETPLACES=EBAY_US,EBAY_DE,EBAY_AU
```

---

## 5) TODO – Implementation Checklist

1. **Env & Config** – Add env vars and read via `config_loader`. .env and .env.example should be in the service's folder
2. **DB Migration (Breaking Change)** – Drop old `products` table, re-init schema; add new columns to `products` and `product_images`.
3. **Auth** – Implement OAuth client‑credentials; fetch and refresh token.
4. **Browse Search Integration** – Implement search call with required filters and params.
5. **Dedup & Normalization** – Deduplicate and normalize results.
6. **Image Pipeline** – Download, resize, and store local & remote URLs; implement cleanup.
7. **Events** – Emit `products.image.ready` per saved image.
8. **Reliability & Limits** – Implement retry, backoff, and rate‑limit handling.
9. **Docs & Tests** – Update README; create unit/integration tests.
10. **Smoke Run** – End‑to‑end test in Sandbox.

---

### 5.1 Phased Execution Plan

- **Phase 0 – Prep:** Env & config setup. (done)
- **Phase 1 – Schema:** DB migration with breaking changes. (done)
- **Phase 2 – Auth:** OAuth implementation. (next - do web search on the eBay docs before doing it)
- **Phase 3 – Search & Merge:** Browse API integration. (do web search on the eBay docs before doing it)
- **Phase 4 – Images & Events:** Image handling and event emission.
- **Phase 5 – Reliability & Tests:** Stability improvements and tests.
- **Phase 6 – Sandbox Smoke:** Final validation.

---

## 6) Minimal Unit Tests

- Verify filter string includes `fieldgroups=EXTENDED`.
- EPID deduplication picks lowest total cost.
- Correct currency formatting.
- Image resize keeps aspect ratio.
- Image storage includes both local & remote URLs; cleanup works.
- Retry logic triggers on transient failures.
- Correct event payload for `products.image.ready`.

