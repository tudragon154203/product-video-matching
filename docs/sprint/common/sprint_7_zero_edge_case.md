# Sprint 7 – Zero Results Edge Case Handling

**Scope:** Ensure that when either Dropship Product Finder finds **0 products/images** or Video Crawler finds **0 videos/keyframes**, the job completes cleanly with **0 matches** without stalling in intermediate phases.

---

## 1) Objectives

- Avoid timeouts or stalled jobs when one or both asset types are missing.
- Preserve event-driven flow by still emitting **batch** and **completed** events with `total_* = 0`.
- Trigger phase transitions automatically when zero-asset jobs are detected.
- Ensure job-level completion (`match.results.completed` and `evidences.generation.completed`) happens without manual intervention.

---

## 2) Changes by Service

### 2.1 Dropship Product Finder (`services/dropship-product-finder`)
- After product collection:
  - If **no products**:
    - Log `"No products/images found – publishing batch=0 and finishing collection"`.
    - Publish **`products.images.ready.batch`** with:
      ```json
      {
        "job_id": "...",
        "event_id": "...",
        "total_images": 0
      }
      ```
    - Skip per-image `products.image.ready` events.
  - Still publish **`products.collections.completed`**.
- **Contracts**: `products_images_ready_batch.json`, `products_collections_completed.json`.

### 2.2 Video Crawler (`services/video-crawler`)
- After video search:
  - If **no videos**:
    - Log `"No videos/keyframes found – publishing batch=0 and finishing collection"`.
    - Publish **`videos.keyframes.ready.batch`** with:
      ```json
      {
        "job_id": "...",
        "event_id": "...",
        "total_keyframes": 0
      }
      ```
    - Skip per-video-frame `videos.keyframes.ready` events.
  - Still publish **`videos.collections.completed`**.
- **Contracts**: `videos_keyframes_ready_batch.json`, `videos_collections_completed.json`.

---

## 3) Vision Services (Embedding / Keypoint)
- On receiving a **batch event with `total_* = 0`**:
  - Immediately publish both `*.embeddings.completed` and `*.keypoints.completed` with zero counts.
  - Example:
    ```json
    {
      "job_id": "...",
      "event_type": "embeddings",
      "total_assets": 0,
      "processed_assets": 0,
      "failed_assets": 0,
      "has_partial_completion": false
    }
    ```
- Applies to:
  - `products.images.ready.batch` → `image.embeddings.completed` & `image.keypoints.completed`
  - `videos.keyframes.ready.batch` → `video.embeddings.completed` & `video.keypoints.completed`
- **Contracts**: `image_embeddings_completed.json`, `image_keypoints_completed.json`, `video_embeddings_completed.json`, `video_keypoints_completed.json`.

---

## 4) Main API – Phase Event Service
- Use `get_job_asset_types(job_id)` to determine required completion events for a job.
- For single-media jobs:
  - If one media type is missing, do **not** wait for its events.
- Transition from **`feature_extraction`** to **`matching`** once all **required** `*.completed` events are received.

---

## 5) Matcher
- If either side (products or videos) is empty:
  - Immediately emit `match.results.completed` with:
    ```json
    {
      "job_id": "...",
      "event_id": "...",
      "total_matches": 0,
      "matches": []
    }
    ```
- **Contract**: `match_results_completed.json`.

---

## 6) Evidence Builder
- On `match.results.completed` with `total_matches = 0`:
  - Immediately emit `evidences.generation.completed`.
- **Contract**: `evidences_generation_completed.json`.

---

## 7) Test Coverage
- **Dropship Product Finder**: test zero products path → assert `batch=0` + `collections.completed` published.
- **Video Crawler**: test zero videos path → assert `batch=0` + `collections.completed` published.
- **Vision Services**: test `batch=0` triggers immediate `*.completed` events.
- **Main API**: test that zero-asset jobs progress through all phases to completion.
- **Matcher/Evidence**: test `0 matches` path emits both completion events.

---

## 8) Acceptance Criteria
- ✅ Zero-asset jobs finish without timeout.
- ✅ All batch events are emitted even when totals are zero.
- ✅ All `*.completed` events for the relevant asset types are emitted immediately.
- ✅ Main API transitions phases without waiting on missing media types.
- ✅ Matching and Evidence stages emit completion events with `0 matches`.

---

**Changelog (One-Liner):**
FEATURE: Zero-asset handling – services now publish batch=0 + immediate completion events to finish jobs with no products/videos.