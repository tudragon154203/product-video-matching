# Event-Driven Microservices – Full Specs (Product ↔ Video Matching, Ảnh-first)

> Phiên bản: v1.0 (local dev) Bus: RabbitMQ • Orchestrator: Prefect • Vector: pgvector (HNSW) • Storage: Local FS • GPU cho Embedding, CPU cho phần còn lại

---

## 1) Mục tiêu & Tiêu chí

- **Input:** Từ khoá ngành (ví dụ: “gối công thái học”).
- **Output:** Danh sách cặp **(Sản phẩm Amazon/eBay, Video VN/Trung)** có **ảnh giống ≥80%**, kèm **score cuối**, **timestamp**, **ảnh bằng chứng**.
- **Nguyên tắc:** So khớp **ảnh-first**; khác nền/ánh sáng/góc chụp vẫn phải match. Ngữ nghĩa chỉ phụ.
- **SLO (MVP):** Precision ≥95% ở `score ≥ 0.80`; throughput \~5k keyframe/ngày trên CPU; YouTube+Bilibili.

---

## 2) Kiến trúc tổng thể

- **Event-driven microservices** (pub/sub qua **RabbitMQ**).
- **Write-path:** Event bus cho pipeline async (collect → frames → features → match → evidence).
- **Read-path:** **Results API** (REST, CQRS read-only) cho n8n/UI.
- **Orchestrator:** **Prefect** điều phối job, phát request events, theo dõi tiến độ.
- **Compute:**
  - **GPU**: Embedding service (CLIP/DINOv2) – base image `pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime`.
  - **CPU**: Keypoint, Matcher, Ingestion, Collector, Results – base image `python:3.10-slim`.
- **Storage:**
  - **Postgres** (metadata + matches); **Alembic** migrations.
  - **pgvector (HNSW)** cho ANN search.
  - **Local filesystem** cho ảnh sản phẩm, keyframe, kp\_blob, evidence.
  - **Redis** (cache/idempotency nhỏ).

---

## 3) Các service

1. **API Gateway** – (optional giai đoạn đầu) cổng vào, route đến Orchestrator/Results.
2. **Orchestrator** – nhận job từ n8n/UI, publish các *request events*, track status.
3. **Results API** – REST read-only: trả products/videos/matches/evidence.
4. **Catalog Collector** – lấy top-K Amazon/eBay, tải gallery, chuẩn hoá ảnh → lưu local.
5. **Media Ingestion** – tìm & tải video (YouTube, Bilibili), trích **keyframe**.
6. **Vision Embedding (GPU)** – sinh **emb\_rgb**/**emb\_gray** từ ảnh SP & keyframe.
7. **Vision Keypoint (CPU)** – trích **keypoint descriptors** (AKAZE/SIFT) → lưu **kp\_blob**.
8. **Vector Index** – upsert/search ANN (pgvector HNSW) cho **product\_images**.
9. **Matcher** – retrieval (embeddings) → rerank (AKAZE/SIFT + **RANSAC**) → aggregate SP↔video.
10. **Evidence Builder** – render ảnh bằng chứng (side-by-side + overlay inliers).
11. **Rules/Config** *(optional)* – quản lý ngưỡng/trọng số theo ngành (hot-reload).

---

## 4) Topics & Contracts (JSON Schema)

Contracts đặt trong `libs/contracts/`, validate ở producer & consumer.

**Topics chính:**

- `products.collect.request` → `{ job_id, industry, top_amz, top_ebay }`
- `products.images.ready` → `{ product_id, image_id, local_path }`
- `videos.search.request` → `{ job_id, industry, queries[], platforms[], recency_days }`
- `videos.keyframes.ready` → `{ video_id, frames:[{ frame_id, ts, local_path }] }`
- `features.ready` → `{ entity_type:"product_image|video_frame", id, emb_rgb, emb_gray, kp_blob_path }`
- `match.request` → `{ job_id, industry, product_set_id, video_set_id, top_k }`
- `match.result` → `{ job_id, product_id, video_id, best_pair:{img_id, frame_id, score_pair}, score, ts }`
- `match.result.enriched` → `{ ... match.result, evidence_path }`

**Ví dụ JSON Schema (rút gọn):**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ProductsImagesReady",
  "type": "object",
  "required": ["product_id", "image_id", "local_path"],
  "properties": {
    "product_id": {"type": "string"},
    "image_id": {"type": "string"},
    "local_path": {"type": "string"}
  }
}
```

---

## 5) Pipeline E2E

1. **Orchestrator** nhận `POST /start-job` → publish `products.collect.request`, `videos.search.request`.
2. **Catalog Collector** tải gallery → `` → publish `products.images.ready`.
3. **Media Ingestion** tải video → trích **3–8 keyframe** (lọc blur) → `` → publish `videos.keyframes.ready`.
4. **Vision Embedding** & **Vision Keypoint** subscribe các sự kiện ready → tạo `` (thêm `kp_blob_path: data/kp/{entity_id}.npz`).
5. **Vector Index** upsert embeddings **product\_images** (ANN).
6. **Orchestrator** publish `match.request` → **Matcher**: retrieval ANN top-K → rerank **AKAZE/SIFT + RANSAC** → aggregate SP↔video → publish `match.result`.
7. **Evidence Builder** render ảnh bằng chứng → `` → publish `match.result.enriched`.
8. **Results API** phục vụ n8n/UI (filter theo `min_score`).

---

## 6) Matching Logic (ảnh-first)

- **Retrieval (ANN):** cosine trên **emb\_rgb/emb\_gray** (lấy max).
- **Rerank:** Keypoint (AKAZE/SIFT) → Lowe ratio → **RANSAC** → `inliers_ratio = inliers / min(kpA, kpB)`.
- **Pair score:**
  ```
  score_pair = 0.35 * sim_deep      # cosine(embeddings)
             + 0.55 * sim_kp        # inliers_ratio sau RANSAC
             + 0.10 * sim_edge      # optional: edge/HOG nếu cần
  ```
- **Quy tắc SP↔video (M ảnh × N frame):**
  - `best = max(score_pair)`; `consistency = số cặp ≥ 0.80`.
  - Nhận nếu **(best ≥ 0.88 & consistency ≥ 2)** hoặc **best ≥ 0.92**.
  - **Accept** nếu `score_video_product ≥ 0.80` (có cộng 0.02 nếu `consistency ≥ 3`, 0.02 nếu `coverage ≥ 2`).

**Mặc định ngưỡng (configurable):** `RETRIEVAL_TOPK=20`, `SIM_DEEP_MIN=0.82`, `INLIERS_MIN=0.35`, `BEST_MIN=0.88`, `CONS_MIN=2`, `ACCEPT=0.80`.

---

## 7) Lược đồ DB (Postgres+pgvector)

- `products(product_id PK, src, asin_or_itemid, title, brand, url, created_at)`
- `product_images(img_id PK, product_id FK, local_path, emb_rgb vector, emb_gray vector, kp_blob_path, phash, created_at)`
- `videos(video_id PK, platform, url, title, duration_s, published_at)`
- `video_frames(frame_id PK, video_id FK, ts, local_path, emb_rgb vector, emb_gray vector, kp_blob_path, created_at)`
- `matches(match_id PK, job_id, product_id FK, video_id FK, best_img_id, best_frame_id, ts, score, evidence_path, created_at)`

Alemic migrations giữ ở `infra/migrations/`.

---

## 8) Project Skeleton (Mono-repo)

```
repo-root/
├─ services/
│  ├─ orchestrator/               # Prefect flows + REST control (start-job, status)
│  ├─ results-api/                # CQRS read-only API cho n8n/UI
│  ├─ catalog-collector/          # Amazon/eBay collector + chuẩn hoá + lưu ./data/products
│  ├─ media-ingestion/            # search + download + keyframes (YouTube/Bilibili)
│  ├─ vision-embedding/           # (GPU) CLIP/DINOv2: emb_rgb/emb_gray
│  ├─ vision-keypoint/            # (CPU) AKAZE/SIFT → kp_blob
│  ├─ vector-index/               # pgvector HNSW + REST /search
│  ├─ matcher/                    # retrieval→RANSAC→aggregate→emit match.result
│  ├─ evidence-builder/           # render side-by-side + overlay inliers
│  └─ rules-config/               # (optional) ngưỡng, trọng số theo ngành
│
├─ libs/
│  ├─ contracts/                  # JSON Schema cho event
│  ├─ common-py/                  # logging, tracing, rabbit, postgres, file io, idempotency
│  └─ vision-common/              # normalize, gray+CLAHE, IO ảnh, RANSAC helpers
│
├─ infra/
│  ├─ pvm/
│  │  └─ docker-compose.dev.yml   # dev local: postgres, rabbitmq, services
│  ├─ migrations/                 # alembic (Postgres schema)
│  └─ k8s/                        # (later) manifests/helm
│
├─ ops/
│  ├─ grafana-dashboards/
│  └─ prom-rules/
│
├─ data/                          # Local storage root (bind mount)
│  ├─ products/<product_id>/<img_id>.jpg
│  ├─ videos/<video_id>/frames/<frame_id>.jpg
│  ├─ kp/<entity_id>.npz
│  └─ evidence/<match_id>.jpg
│
├─ scripts/                       # seed, smoke tests
├─ .env.example                   # biến môi trường mẫu

└─ README.md
```

**docker-compose.dev.yml (rút gọn):**

```yaml
version: "3.9"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: dev
    ports: ["5432:5432"]
  rabbitmq:
    image: rabbitmq:3-management
    ports: ["5672:5672", "15672:15672"]
  results-api:
    build: ./services/results-api
    env_file: .env
    volumes: ["./data:/app/data"]
    ports: ["8080:8080"]
  orchestrator:
    build: ./services/orchestrator
    env_file: .env
    depends_on: [rabbitmq]
  catalog-collector:
    build: ./services/catalog-collector
    env_file: .env
    volumes: ["./data:/app/data"]
    depends_on: [rabbitmq]
  media-ingestion:
    build: ./services/media-ingestion
    env_file: .env
    volumes: ["./data:/app/data"]
    depends_on: [rabbitmq]
  vision-embedding:
    build: ./services/vision-embedding
    env_file: .env
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
    volumes: ["./data:/app/data"]
  vision-keypoint:
    build: ./services/vision-keypoint
    env_file: .env
    volumes: ["./data:/app/data"]
  vector-index:
    build: ./services/vector-index
    env_file: .env
  matcher:
    build: ./services/matcher
    env_file: .env
    volumes: ["./data:/app/data"]
  evidence-builder:
    build: ./services/evidence-builder
    env_file: .env
    volumes: ["./data:/app/data"]
```





**.env.example**

```
POSTGRES_DSN=postgresql://postgres:dev@localhost:5432/product_video_matching
BUS_BROKER=amqp://guest:guest@localhost:5672/
DATA_ROOT=./data
EMBED_MODEL=clip-vit-b32
RETRIEVAL_TOPK=20
SIM_DEEP_MIN=0.82
INLIERS_MIN=0.35
MATCH_BEST_MIN=0.88
MATCH_CONS_MIN=2
MATCH_ACCEPT=0.80
```

**Prefect (start-job flow) – khung tối giản:**

```python
from prefect import flow, task

@task
def emit_collect(industry, top_amz, top_ebay):
    # publish products.collect.request
    pass

@task
def emit_video_search(industry, queries, platforms, days):
    # publish videos.search.request
    pass

@flow
def start_job(industry: str, top_amz: int = 10, top_ebay: int = 10):
    emit_collect.submit(industry, top_amz, top_ebay)
    emit_video_search.submit(industry, [industry], ["youtube", "bilibili"], 365)
    return {"job_id": "..."}
```

**Endpoints tóm tắt:**

- `POST /orchestrator/start-job` → `{ job_id }`
- `GET /status/{job_id}` → `{ phase, percent, counts }`
- `GET /results?industry=&min_score=` → danh sách match
- `GET /products/{id}` / `GET /videos/{id}` / `GET /matches/{match_id}`

---

## 9) Retry, DLQ, Idempotency, Logging

- **Retry:** exponential backoff, tối đa 3 lần; sau đó đẩy **DLQ** (dead-letter queue) theo topic tương ứng.
- **Idempotency:** key = hash(`local_path` hoặc `url+ts`) để tránh xử lý lặp.
- **Logging:** JSON logs; mã lỗi rõ ràng (retryable vs fatal).
- **Tracing/Metrics (optional MVP):** OpenTelemetry, Prometheus (qps, latency, queue depth, precision offline).

---

## 10) Base Docker Images

- **GPU services:** `pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime`
- **CPU services:** `python:3.10-slim`

---

## 11) Sprint 1 – TODO List (MVP khả dụng)

**Phạm vi Sprint 1:** Amazon/eBay + YouTube; matching ảnh-first (retrieval→rerank→aggregate); Results API; chạy local bằng docker-compose.

**Công việc bắt buộc:**

1. **Repo & Compose**
   -
2. **Contracts & Topics**
   -
3. **Catalog Collector (Amazon/eBay)**
   -
4. **Media Ingestion (YouTube)**
   -
5. **Vision Embedding (GPU/hoặc CPU fallback)**
   -
6. **Vision Keypoint (CPU)**
   -
7. **Vector Index (pgvector)**
   -
8. **Matcher**
   -
9. **Evidence Builder**
   -
10. **Results API**

-

11. **Smoke E2E & Chất lượng**

-

**Kết quả Sprint 1:**

- Gọi `POST /orchestrator/start-job` với 1 keyword → sau \~vài phút → `GET /results?min_score=0.8` cho ra ≥1 match đúng, có ảnh bằng chứng.

---

## 12) Ghi chú vận hành

- **Batching** ở Embedding GPU (32–64) để tận dụng phần cứng.
- **Feature flags**: bật/tắt Gray+CLAHE, segmentation, edge/HOG.
- **Fallback**: nếu không có GPU, dùng CLIP CPU (chậm hơn) + tăng top-K để bù.
- **Scale-up Phase 2**: thêm Bilibili/Douyin/XHS, DINOv2-B, SuperPoint/SuperGlue, Results cache, Orchestrator nâng cấp.

