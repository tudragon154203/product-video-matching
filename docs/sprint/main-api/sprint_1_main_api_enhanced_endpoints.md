# Main API — Enhanced Endpoints (v1)

> Read‑only polling endpoints, timestamps in GMT+7, no prefix/base.

---

## 1) Job phase / status

### `GET /status/{job_id}`

Snapshot for header & overall progress.

```json
{
  "job_id": "j_123",
  "phase": "feature_extraction",
  "percent": 62.5,
  "counts": { "products": 120, "videos": 34, "images": 600, "frames": 2400 },
  "updated_at": "2025-08-23T14:25:00+07:00"
}
```

---

## 2) Downloaded videos

### `GET /jobs/{job_id}/videos`

Query: `q`, `platform`, `min_frames`, `limit`, `offset`, `sort_by=updated_at|duration_s|frames_count|title`, `order`

```json
{
  "items": [
    {
      "video_id": "v_abc",
      "platform": "youtube",
      "url": "https://youtube.com/...",
      "title": "Test API Video",
      "duration_s": 120,
      "frames_count": 480,
      "updated_at": "2025-08-23T14:20:10+07:00"
    }
  ],
  "total": 34, "limit": 20, "offset": 0
}
```

### `GET /jobs/{job_id}/videos/{video_id}/frames`

Query: `limit`, `offset`, `sort_by=ts|frame_id`, `order`

```json
{
  "items": [
    {
      "frame_id": "v_abc_frame_000123",
      "ts": 30.0,
      "local_path": "/data/frames/v_abc/000123.jpg",
      "updated_at": "2025-08-23T14:22:41+07:00"
    }
  ],
  "total": 480, "limit": 20, "offset": 0
}
```

---

## 3) Downloaded images (products)

### `GET /jobs/{job_id}/images`

Query: `product_id`, `q`, `limit`, `offset`, `sort_by=img_id|updated_at`, `order`

```json
{
  "items": [
    {
      "img_id": "p_001_img_0",
      "product_id": "p_001",
      "local_path": "/data/products/p_001/0.jpg",
      "product_title": "NeckCare Pillow V2",
      "updated_at": "2025-08-23T14:21:44+07:00"
    }
  ],
  "total": 600, "limit": 20, "offset": 0
}
```

---

## 4) Features (segment / embedding / keypoints)

> DB columns: `seg_mask_path`, `emb_rgb`, `kp_blob_path` on `product_images` + `video_frames`.

### 4.1 Job summary

`GET /jobs/{job_id}/features/summary`

```json
{
  "job_id": "j_123",
  "product_images": {
    "total": 600,
    "segment":   { "done": 380,  "percent": 63.33 },
    "embedding": { "done": 410,  "percent": 68.33 },
    "keypoints": { "done": 395,  "percent": 65.83 }
  },
  "video_frames": {
    "total": 2400,
    "segment":   { "done": 900,  "percent": 37.50 },
    "embedding": { "done": 1320, "percent": 55.00 },
    "keypoints": { "done": 1180, "percent": 49.17 }
  },
  "updated_at": "2025-08-23T14:25:00+07:00"
}
```

### 4.2 List product images

`GET /jobs/{job_id}/features/product-images` Query: `has=segment|embedding|keypoints|none|any`, `limit`, `offset`, `sort_by=updated_at|img_id`, `order`

```json
{
  "items": [
    {
      "img_id": "p_001_img_0",
      "product_id": "p_001",
      "has_segment": true,
      "has_embedding": true,
      "has_keypoints": false,
      "paths": { "segment": ".../seg.png", "embedding": ".../emb.bin", "keypoints": null },
      "updated_at": "2025-08-23T14:22:41+07:00"
    }
  ],
  "total": 600, "limit": 20, "offset": 0
}
```

### 4.3 List video frames

`GET /jobs/{job_id}/features/video-frames` Query: `video_id` (optional), `has=segment|embedding|keypoints|none|any`, `limit`, `offset`, `sort_by=updated_at|frame_id|ts`, `order`

```json
{
  "items": [
    {
      "frame_id": "v_abc_frame_000123",
      "video_id": "v_abc",
      "ts": 30.0,
      "has_segment": false,
      "has_embedding": true,
      "has_keypoints": true,
      "paths": { "segment": null, "embedding": ".../emb.bin", "keypoints": ".../kp.bin" },
      "updated_at": "2025-08-23T14:23:41+07:00"
    }
  ],
  "total": 2400, "limit": 20, "offset": 0
}
```

### 4.4 Asset detail

`GET /features/product-images/{img_id}`

```json
{
  "img_id": "p_001_img_0",
  "product_id": "p_001",
  "has_segment": true,
  "has_embedding": true,
  "has_keypoints": false,
  "paths": { "segment": ".../seg.png", "embedding": ".../emb.bin", "keypoints": null },
  "updated_at": "2025-08-23T14:22:41+07:00"
}
```

`GET /features/video-frames/{frame_id}`

```json
{
  "frame_id": "v_abc_frame_000123",
  "video_id": "v_abc",
  "ts": 30.0,
  "has_segment": false,
  "has_embedding": true,
  "has_keypoints": true,
  "paths": { "segment": null, "embedding": ".../emb.bin", "keypoints": ".../kp.bin" },
  "updated_at": "2025-08-23T14:23:41+07:00"
}
```

---

## Notes

- All timestamps in `+07:00`.
- Pagination + sorting unified across endpoints.
- No SSE; client polls these endpoints.
- No authentiation
