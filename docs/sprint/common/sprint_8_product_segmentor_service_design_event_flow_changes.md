# Product Segmentor Service – Design & Event Flow Changes

> Purpose: Insert a **product-segmentation stage** before `vision-embedding` and `vision-keypoint` to focus all features on the product region (masking people/background). This improves cosine retrieval and keypoint matching on catalog ↔ keyframe pairs.

---

## 1. Position in Pipeline

```
(1) Dropship Product Finder ──► products.image.ready(.batch)
(2) Video Crawler         ───► video.keyframes.ready(.batch)
(3) Product Segmentor
      ├─► (4) products.images.masked(.batch)
      └─► (5) video.keyframes.masked(.batch)
(6) Vision Embedding
(7) Vision Keypoint
```

- Segmentor subscribes **only** to `*.ready` & `*.ready.batch`.
- Publishes **per-asset masked** and **per-job masked.batch** events.
- Downstream services **switch** to masked topics exclusively (no longer read `*.ready`).

---

## 2. New Event Contracts

### 2.1 `products.image.masked` (per asset)

```json
{
  "event_id": "uuid4",
  "job_id": "string",
  "image_id": "string",
  "mask_path": "data/masks/products/<image_id>.png"
}
```

### 2.2 `products.images.masked.batch` (per job; counts)

```json
{
  "event_id": "uuid4",
  "job_id": "string",
  "total_images": 12
}
```

### 2.3 `video.keyframes.masked` (per asset, example)

```json
{
  "event_id": "uuid4",
  "job_id": "string",
  "video_id": "string",
  "frames": [
    {
      "frame_id": "string",
      "ts": 12.4,
      "mask_path": "data/masks/frames/<frame_id>.png"
    }
  ]
}
```

### 2.4 `video.keyframes.masked.batch` (per job; counts)

```json
{
  "event_id": "uuid4",
  "job_id": "string",
  "total_keyframes": 340
}
```

---

## 3. Changes to Existing Contracts & Flow

### 3.1 Upstream producers (no schema change)

- `products.image.ready` and `video.keyframes.ready` remain unchanged but now feed **Product Segmentor**.

### 3.2 Downstream consumers behavior change

- **Vision Embedding** & **Vision Keypoint**:
  - Subscribe to `products.images.masked(.batch)` and `video.keyframes.masked(.batch)`.
  - Maintain per-asset state `{has_mask, mask_path}`.
  - Start processing when either:
    1. Masked event arrives before watermark W ⇒ process masked asset.
    2. Watermark expires ⇒ process raw asset (to avoid blocking).

### 3.3 New routing keys

- Exchange: `events` (topic)
  - `products.image.masked`
  - `products.images.masked.batch`
  - `video.keyframes.masked`
  - `video.keyframes.masked.batch`

---

## 4. Orchestration & Completion Semantics

- Product Segmentor emits per-asset and per-job batch events.
- Embedding/Keypoint consume masked events instead of the original `.ready` events.
- Job completion unchanged; relies on embedding/keypoint `.completed` events.

---

## 5. ASCII Event Swimlane (Vertical)

```
(1) Collector
    │
    ▼
products.images.ready(.batch)
    │
    ▼
(3) Product Segmentor
    │
    ▼
products.images.masked(.batch)
    │
    ▼
(6) Vision Embedding +(7) Vision Keypoint

(2) Collector
    │
    ▼
video.keyframes.ready(.batch)
    │
    ▼
(3) Product Segmentor
    │
    ▼
video.keyframes.masked(.batch)
    │
    ▼
(6) Vision Embedding +(7) Vision Keypoint

```

---

---

## 7. Phases

**Goal:** ship Product Segmentor safely with minimal churn to downstream services.

### Phase 1 – Prep & Contracts

- Finalize schemas, routing keys, and DB changes.
- Write migration for `masked_local_path`.

### Phase 2 – Mock Service (Event Plumbing)

- Create skeleton service.
- Listen to `.ready` events, publish mock `.masked` events.
- Verify downstream integration without real model.

### Phase 3 – Downstream Integration

- Switch embedding/keypoint to masked topics.

---

## 8. Service Skeleton (filesystem layout)

> Mô phỏng cùng phong cách `vision-embedding` trong ảnh: có `handlers/`, `services/`, `config_loader.py`, `main.py`, `requirements.txt`, `Dockerfile`, `README.md`.

```
services/product-segmentor/
├── README.md
├── requirements.txt
├── Dockerfile
├── config_loader.py
├── main.py
├── segmentor.py               # core business logic (later: RMBG/YOLO/SAM)
├── handlers/
  │  decorators.py
  |  segmentor_handler.py
└── services/
    ├── service.py # Main service
```

