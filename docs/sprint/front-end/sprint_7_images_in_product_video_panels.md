
# Spec — Thumbnails in Products & Video Panels

## 1) Objective

Display product/video thumbnails in list rows and grids with a small, consistent visual, while keeping pages fast and responsive.

---

## 2) Current State vs Planned Changes

### ProductsPanel

**Current**

* Rows show **text info only** (product title, meta).
* No thumbnail rendered.
* Skeleton/empty/error states exist but  **no image placeholder** .
* Data already includes `file_path` from backend, but FE ignores it.

**Planned Change**

* Add a **120×120 thumbnail** at the start of each row.
* `src` built from `NEXT_PUBLIC_API_BASE_URL + file_path`.
* Fallback: placeholder if missing/error.
* `alt` = product title (else `""\`).
* Use only the **first image** of the product (ignore additional ones).
* Lazy loading for all thumbnails; no prefetch for off-page items.
* Skeleton updated to reserve a 120×120 block during loading.

---

### VideoPanel

**Current**

* Video list shows **video metadata** (status, title, etc).
* No preview image of associated video.
* Panels rely on TanStack Query states (loading, error, empty).

**Planned Change**

* Add a **120×120 thumbnail** for each video row, sourced from the **first video keyframe** (`file_path`).
* `src` built the same way: `BASE + file_path`.
* Placeholder if missing/error.
* `alt` = video title (else `""\`).
* Thumbnails lazy-loaded and fixed-size, maintaining layout consistency.
* Skeleton/empty/error screens updated to show a reserved thumbnail box.

---

## 3) Data Contract (Frontend expectations)

* FE reads **`file_path`** from the API response.
* FE forms the image URL as:

  `IMG_URL = NEXT_PUBLIC_API_BASE_URL + file_path`
* For products/videos with multiple images or frames: **only the first one** is used.
* If `file_path` is missing/empty, treat as “no image”.

---

## 4) Rendering Rules

* **Renderer** : `next/image` (App Router).
* **Size** : square thumbnail, **120×120 px** (fixed).
* **Alt text** : product title in ProductsPanel; video title in VideoPanel.
* **Lazy loading** : `loading="lazy"`.
* **Placeholder** : if image fails/missing, show static placeholder.
* **Never leak internal paths** .

---

## 5) Accessibility & i18n

* Every thumbnail has an `alt` from the appropriate title.
* Placeholder uses `alt=""`.

---

## 6) Performance & Caching

* Fixed 120×120 container prevents layout shift.
* Lazy load + pagination integration ensures no offscreen requests.
* Cache headers controlled by backend; FE does not override.

---

## 7) Acceptance Criteria (DoD)

* ✅ Thumbnails appear in both ProductsPanel & VideoPanel.
* ✅ Each image is 120×120 px, cropped cover, no layout shift.
* ✅ Uses only the **first product image** or  **first video keyframe** .
* ✅ Uses `file_path` to build URL; never shows local path.
* ✅ Placeholder shown if missing/404.
* ✅ Alt text = product/video title (else `""\`).
* ✅ Lazy loading active; offscreen images not requested.
* ✅ Skeletons/empty/error UIs reserve space for thumbnails.

---

## 8) Test-Driven Development (TDD)

### Unit (Jest + RTL)

* URL formed correctly from `file_path`.
* Placeholder renders on missing path/error.
* Alt text rules respected.
* Fixed box always 120×120.
* Only the first image/frame is used.

### Integration

* Pagination + lazy load works (only viewport items requested).
* Skeleton reserves image space during loading.

### E2E (Playwright)

* Thumbnails visible on ProductsPanel & VideoPanel lists.
* Scroll triggers lazy load requests.
* Placeholder shown on 404.
* Alt text matches product/video title.
* No internal FS paths appear in DOM.
