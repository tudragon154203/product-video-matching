# Sprint 8 – eBay Integration for Dropship Product Finder

> Goal: Integrate eBay **Browse API** into the `dropship-product-finder` service according to the agreed business constraints. Maintain the image‑first pipeline (download images → emit `products.images.ready`) without requiring changes to downstream services.

> **Note:** This implementation will initially run in the **eBay Sandbox** environment. The `.env` file for the `dropship-product-finder` service will include `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET`. These will be read via `config_loader` and used within the application. The service should obtain a fresh `access_token` at startup by calling **Step 1 – Get access token**: send a POST request to `/identity/v1/oauth2/token` with Basic Auth `<CLIENT_ID>:<CLIENT_SECRET>` and receive an `access_token` (usually valid for \~2 hours).

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
- **top\_ebay:** value comes from the `main-api` service request payload.
- **Retry:** 3 times on HTTP errors; skip item if still failing.
- **Affiliate/EPN:** not used.
- **Enrich:** do not call `getItem` if search already provides price/shipping info.
- **Database:** **Breaking change** – drop the existing `products` table and re‑initialize. Add two new columns:
  - `marketplace` – enum (`us`, `de`, `au`).
  - `price` – string including currency (e.g., `$20`, `€3`, `5 AUD`).

---

## 2) Integration with Existing Pipeline

- **Consumer input:** listens to `products.collect.request`. Takes `queries.en` and `top_ebay` from payload.
- **eBay Collector:** calls Browse Search with filters in §3, merges results from configured marketplaces, deduplicates by EPID, downloads & resizes images.
- **Producer output:** emits `products.images.ready` for each image.
- **Downstream:** No changes to other services.

---

## 3) eBay Collector Design

**Related eBay Docs:**

- [eBay Buy APIs Overview](https://developer.ebay.com/api-docs/buy/overview.html)
- [Browse API v1](https://developer.ebay.com/api-docs/buy/browse/overview.html)
- [Identity (OAuth) API](https://developer.ebay.com/api-docs/commerce/identity/overview.html)

### 3.1 Access Token Retrieval

- **POST** `/identity/v1/oauth2/token` with Basic Auth `<CLIENT_ID>:<CLIENT_SECRET>`.
- Sandbox: `https://api.sandbox.ebay.com`.
- Body: `grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope`.
- Retrieve token at service startup; refresh before expiry or on `401`.

### 3.2 Browse Search

- **GET** `/buy/browse/v1/item_summary/search`.
- Headers: Bearer token, `X-EBAY-C-MARKETPLACE-ID`.
- Filters:

```
buyingOptions:{FIXED_PRICE},returnsAccepted:true,deliveryCountry:US,maxDeliveryCost:0,price:[10..40],priceCurrency:USD,conditionIds:{1000}
```

### 3.3 Deduplication & Images

- Deduplicate by `epid` (fallback `itemId`).
- Download all images, resize to \~400px, retry failed downloads ×3.

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

- Add env vars & read via `config_loader`.
- DB migration: **drop old **``** table** (breaking change) and re‑initialize with `marketplace` enum and `price` string columns.
- Implement OAuth token retrieval on service startup.
- Implement Browse Search call with fixed filters and dynamic params.
- Deduplicate results and normalize fields.
- Download & resize images; emit `products.images.ready`.
- Add retries & error handling.
- Test in sandbox environment.
- Update README and logs.
- Perform smoke run.

---

## 6) Minimal Unit Tests

- **Filter Builder Test:** verify correct filter string for API call.
- **Deduplication Test:** ensure EPID dedup picks lowest total cost.
- **Price Formatting Test:** check correct currency symbol/code usage.
- **Image Resize Test:** verify aspect ratio preserved, longest side \~400px.
- **Retry Logic Test:** mock transient 5xx and ensure retries happen.
- **Event Emission Test:** confirm correct payload structure for `products.images.ready`.

