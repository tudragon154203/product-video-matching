# Sprint 2.5 — Inline Image Fields on Products/Videos (Spec)

## Overview
- Goal: Front-end avoids nested calls by receiving representative image fields directly on products and videos list endpoints used by the panel.
- Scope: Non-breaking additive fields only. API.md remains unchanged until implementation merges; this spec governs the change.

## Endpoints In Scope
- GET `/jobs/{job_id}/videos` — add preview image fields.
- GET `/jobs/{job_id}/products` — add primary image fields. If this endpoint does not yet exist, treat this as the contract for when it does or when an equivalent list endpoint is exposed by results-api.

## Additive Fields
### Videos: GET /jobs/{job_id}/videos
Each `items[]` object adds the following nullable fields:
- `thumbnail_url`: Public URL for the platform thumbnail if available (e.g., YouTube/TikTok). Example: `/files/videos/thumbnails/vid-123.jpg`.
- `preview_frame`: Object with the best available frame to preview the video content.
  - `frame_id`: ID of selected frame.
  - `ts`: Timestamp (seconds) of the frame.
  - `url`: Public URL to the raw frame image.
  - `segment_url`: Public URL to the masked/segmented frame image, if exists; else null.

Example item (truncated):
```jsonc
{
  "video_id": "vid-123",
  "platform": "youtube",
  "title": "Example",
  "duration_s": 120.5,
  "frames_count": 240,
  "thumbnail_url": "/files/videos/thumbnails/vid-123.jpg",  // NEW
  "preview_frame": {                                          // NEW
    "frame_id": "frame-789",
    "ts": 37.2,
    "url": "/files/videos/frames/frame-789.jpg",
    "segment_url": "/files/masked/frame-789.jpg"
  },
  "updated_at": "2024-01-15T10:30:00+07:00"
}
```

Selection rules for `preview_frame` (best-effort, deterministic):
1) Prefer a frame with `has_segment == true` and valid `local_path` for the segment.
2) Else pick a frame with valid raw image path.
3) Prefer middle timestamp (~duration/2); break ties by newest `updated_at` then lowest `frame_id`.
4) If no frames or invalid paths, set `preview_frame = null`.

### Products: GET /jobs/{job_id}/products
Each `items[]` object adds the following nullable fields:
- `primary_image_url`: Public URL of the representative product image (original).
- `primary_masked_url`: Public URL of the masked/segmented variant, if produced; else null.
- `image_count`: Integer count of images available for the product (for quick UI hints).

Example item (truncated):
```jsonc
{
  "product_id": "prod-456",
  "marketplace": "amazon",
  "title": "Ergonomic Pillow",
  "brand": "Acme",
  "url": "https://amazon.com/...",
  "image_count": 4,                              // NEW
  "primary_image_url": "/files/images/img-123.jpg",      // NEW
  "primary_masked_url": "/files/masked/img-123.jpg",     // NEW
  "updated_at": "2024-01-15T10:30:00+07:00"
}
```

Selection rules for `primary_*` (best-effort, deterministic):
1) Choose the product image most recently updated.
2) Prefer images that have a masked variant available for `primary_masked_url`.
3) Break ties by lowest `img_id`.
4) If no valid images or paths, set both URLs to null and `image_count = 0`.

## URL Formation
- Derive all URLs from existing `local_path` fields under `DATA_ROOT_CONTAINER`, mounted at `/files` (see sprint_2_serve_images_spec.md).
- Normalize separators to `/`, disallow path traversal; if derivation fails, return null.
- URLs are relative (`/files/...`). FE composes with `NEXT_PUBLIC_API_BASE_URL`.

## Non-Goals
- No removal or renaming of existing fields.
- No new heavy queries; selection uses existing tables/indices.
- No image transformations (thumbnails are assumed pre-generated if used).

## Acceptance Criteria
- Videos list returns `thumbnail_url` and `preview_frame` per item with correct URLs or nulls.
- Products list returns `image_count`, `primary_image_url`, and `primary_masked_url` per item with correct URLs or nulls.
- When source files are missing, fields are null; endpoints still return 200 with items listed.
- Sorting, pagination, and existing filters remain unchanged and performant.
- Backward compatibility maintained; existing consumers unaffected.

## Validation & Tests (TDD Outline)
- Unit: URL derivation function returns `/files/...` for valid paths, null for invalid; handles Windows and POSIX paths.
- Unit: Frame selector follows priority rules and is deterministic for same inputs.
- Unit: Product image selector follows priority rules and is deterministic for same inputs.
- Integration: Seed minimal data; list endpoints include new fields; URLs resolve (200) for seeded files; 404 for missing files handled gracefully by FE.

## Performance Notes
- Avoid N+1 queries: join or lateral selects to fetch one representative image/frame and counts in the same query when possible.
- Index usage: ensure indices on `(product_id)`, `(video_id)`, and timestamps used by selectors.

## Rollout
- Implement behind a feature flag `INCLUDE_INLINE_IMAGE_FIELDS` defaulting to enabled in dev.
- Document changes in API.md after implementation stabilizes.

