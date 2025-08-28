# Microservices Event System Redesign

Hệ thống events mới được thiết kế dựa trên schema hiện tại, được chuẩn hoá để quản lý pha (phase management) rõ ràng. Mỗi `.completed` event **bắt buộc** chứa `job_id` và `event_id`, giúp đồng bộ song song và nối tiếp giữa các microservice.

```
[Client/UI] → Main API (Phase Manager) → RabbitMQ
         ├── Dropship Product Finder ──▶ products.collections.completed {job_id, event_id}
         └── Video Crawler ────────────▶ videos.collections.completed {job_id, event_id}

(products.collections.completed + videos.collections.completed) → Barrier → Vision Embeddings & Vision Keypoints (song song)

Vision Embedding (image, per_asset) → image.embedding.ready {job_id, asset_id, event_id}
Vision Keypoint (image, per_asset)  → image.keypoint.ready {job_id, asset_id, event_id}
Vision Embedding (video, per_asset) → video.embedding.ready {job_id, asset_id, event_id}
Vision Keypoint (video, per_asset)  → video.keypoint.ready {job_id, asset_id, event_id}

(image.embeddings.completed + video.embeddings.completed + image.keypoints.completed + video.keypoints.completed) → Barrier → Matcher → matchings.process.completed {job_id, event_id}

matchings.process.completed → Evidence Builder → evidences.generation.completed {job_id, event_id} → Results API → Client
```

## Nguyên tắc
- Mỗi `.completed` bắt buộc có `job_id` và `event_id` (uuidv4) để Phase Manager quản lý và tránh trùng.
- Các sự kiện `ready` là **per_asset** (theo từng ảnh hoặc keyframe), còn các `.completed` là **per-job** (mỗi nhánh/pha 1 lần cho một `job_id`).
- Phase Manager chỉ dựa trên `.completed` để chuyển pha (không đếm asset, không phụ thuộc thứ tự).
- Song song được đồng bộ bằng **barrier**: chỉ khi đủ event mới sang pha mới.
- Đã bỏ `match.result.enriched` để tránh nhầm với `match.result`.
- Loại bỏ hoàn toàn `features.extraction.completed` vì đã thay bằng các `.completed` cụ thể hơn.

## Danh sách events
- `products.collections.completed`
- `videos.collections.completed`
- `image.embedding.ready` (per_asset)
- `image.embeddings.completed` (per-job)
- `image.keypoint.ready` (per_asset)
- `image.keypoints.completed` (per-job)
- `video.embedding.ready` (per_asset)
- `video.embeddings.completed` (per-job)
- `video.keypoint.ready` (per_asset)
- `video.keypoints.completed` (per-job)
- `matchings.process.completed`
- `evidences.generation.completed`

## Điều kiện chuyển pha
| Pha hiện tại        | Điều kiện                                                                                                       | Pha kế tiếp         |
| ------------------- | --------------------------------------------------------------------------------------------------------------- | ------------------- |
| collection          | products & videos collections                                                                                   | feature_extraction  |
| feature_extraction  | image.embeddings.completed + video.embeddings.completed + image.keypoints.completed + video.keypoints.completed | matching            |
| matching            | matchings.process.completed                                                                                     | evidence            |
| evidence            | evidences.generation.completed                                                                                  | completed           |

## Payload chuẩn
**Per-asset:**
```json
{
  "job_id": "string",
  "asset_id": "string",
  "event_id": "uuidv4"
}
```

**Per-job (`.completed`):**
```json
{
  "job_id": "string",
  "event_id": "uuidv4"
}
```

## Dư thừa từ hệ thống cũ sau khi áp dụng mới
- `features.extraction.completed` → Bỏ hẳn, đã tách thành `*.embeddings.completed` và `*.keypoints.completed`.
- `match.result.enriched` → Bỏ, tránh trùng với `match.result`.
- Các event `.completed` không chứa `job_id` → Bỏ hoặc sửa lại để đúng format.
- Các trạng thái trung gian không dùng trong phase management → Chỉ giữ nếu còn giá trị debug hoặc logging.

---

## TODO – Dọn dẹp & Triển khai (Full checklist)

### 1) Contracts/Schemas
- [ ] Thêm mới các schemas:
  - [ ] `image_embedding_ready.json`, `video_embedding_ready.json`
  - [ ] `image_keypoint_ready.json`, `video_keypoint_ready.json`
  - [ ] `products_collections_completed.json`, `videos_collections_completed.json`
  - [ ] `image_embeddings_completed.json`, `video_embeddings_completed.json`
  - [ ] `image_keypoints_completed.json`, `video_keypoints_completed.json`
  - [ ] `matchings_process_completed.json`, `evidences_generation_completed.json`
- [ ] Cập nhật **registry/index** để nạp các schema mới.
- [ ] Viết test validator cho tất cả schemas mới.
- [ ] Đánh dấu @deprecated và **xoá** sau khi switch: `features_extraction_completed.json`, `match_result_enriched.json`.

### 2) Main API (Phase Manager)
- [ ] Tạo bảng `phase_events(event_id PK, job_id, name, received_at)` và cột `phase` trong `jobs` (nếu chưa có).
- [ ] Subscribe các topic: `products.collections.completed`, `videos.collections.completed`, `image.embeddings.completed`, `video.embeddings.completed`, `image.keypoints.completed`, `video.keypoints.completed`, `matchings.process.completed`, `evidences.generation.completed`.
- [ ] Implement dedup theo `event_id` và barrier theo bảng pha.
- [ ] Khi qua barrier Vision (đủ 4 completed) → publish `match.request {job_id}` (giữ schema cũ).
- [ ] Bỏ logic đếm `features.ready`/`FeatureCompletionTracker` liên quan phase.
- [ ] API status: tính % tiến độ dựa trên phase mới (không dựa asset count).
- [ ] Unit & integration tests cho transitions và idempotency.

### 3) Vision Embedding
- [ ] Consume `products.images.ready` và `videos.keyframes.ready` như hiện tại.
- [ ] Thay output: **không** publish `features.ready`; thay bằng `image.embedding.ready`/`video.embedding.ready` (per-asset).
- [ ] Khi hoàn tất theo `job_id`: publish `image.embeddings.completed` và `video.embeddings.completed` (mỗi loại 1 lần/job).
- [ ] Đảm bảo idempotent: UNIQUE theo `(job_id, asset_id)` khi ghi DB; `event_id` cho publish.
- [ ] Tests: per-asset ready & per-job completed.

### 4) Vision Keypoint
- [ ] Consume `products.images.ready`, `videos.keyframes.ready`.
- [ ] Thay output: `image.keypoint.ready`/`video.keypoint.ready` (per-asset).
- [ ] Khi hoàn tất theo `job_id`: publish `image.keypoints.completed` và `video.keypoints.completed`.
- [ ] Tests tương tự Vision Embedding.

### 5) Dropship Product Finder
- [ ] Giữ `products.collect.request` & `products.image.ready` như cũ.
- [ ] Khi xong job: publish `products.collections.completed`.
- [ ] Test end-to-end nhánh products.

### 6) Video Crawler
- [ ] Giữ `videos.search.request` & `videos.keyframes.ready` như cũ.
- [ ] Khi xong job: publish `videos.collections.completed`.
- [ ] Test end-to-end nhánh videos.

### 7) Matcher
- [ ] Consume `match.request` (schema cũ).
- [ ] Publish `match.result` cho từng cặp; **không** dùng `match.result.enriched` nữa.
- [ ] Khi xong job: publish `matchings.process.completed`.
- [ ] Tests: verify publish `matchings.process.completed` đúng 1 lần/job.

### 8) Evidence Builder
- [ ] Consume `match.result`.
- [ ] Khi xong job: publish `evidences.generation.completed`.
- [ ] Tests: verify publish đúng 1 lần/job.

### 9) Observability
- [ ] Cập nhật dashboard/alerts cho events mới (`*_completed`, `*_ready`).
- [ ] Thêm metrics: `phase_state{phase}`, `events_total{event_name}`.
- [ ] Xoá panels cũ dựa trên `features.extraction.completed`/`match.result.enriched`.

### 10) CI/CD & Lint
- [ ] Thêm check **fail build** nếu repo còn chuỗi `features.extraction.completed|match.result.enriched` (pre-commit hoặc job CI với `rg`).
- [ ] Pipeline test: chạy integration flow đầy đủ từ start-job → completed.

### 11) Infra (RabbitMQ)
- [ ] Tạo/bind queues cho các routing keys mới.
- [ ] Viết script dọn queue/binding cũ.
- [ ] Dry-run trên staging: drain → cutover → delete.

### 12) Cleanup code & docs
- [ ] Search & remove references cũ:
  - `rg -n "features.extraction.completed|match.result.enriched"`
  - `sd -s "match.result.enriched" "match.result" -f`
- [ ] Update README/diagrams (đã cập nhật doc này).

### 13) Acceptance Criteria (điều kiện bàn giao)
- [ ] Mọi `.completed` publish/consume đều có `{job_id, event_id}`; idempotent OK.
- [ ] Main API chuyển pha đúng theo barrier **4 completed** ở Vision.
- [ ] Không còn bất kỳ publish/subscribe event cũ.
- [ ] E2E xanh trên staging: start-job → collections.completed(2) → (embedding+keypoint).completed(4) → matching → evidence → completed.
- [ ] Dashboards/alerts hoạt động với events mới.

---

## TODO – Dọn dẹp schemas/events cũ (sau khi switch sang hệ mới)
- [ ] Xoá schema `features_extraction_completed.json` và cập nhật code sử dụng sang các event mới.
- [ ] Xoá schema `match_result_enriched.json` và thay thế bằng `match_result.json`.
- [ ] Chuẩn hoá tất cả `.completed` events để luôn có `{ job_id, event_id }`.
- [ ] Xoá producer phát `features.extraction.completed` và `match.result.enriched` trong code.
- [ ] Xoá consumer subscribe các event cũ trong Main API, Matcher, Evidence Builder.
- [ ] Cập nhật toàn bộ tài liệu (README, diagrams) bỏ đề cập events cũ.
- [ ] Xoá hoặc đổi tên các file test liên quan events cũ.
- [ ] Chạy tìm kiếm toàn repo (`rg -n "features.extraction.completed|match.result.enriched"`) và xoá sạch.
- [ ] Cập nhật dashboard, alert, metric bỏ các event cũ.
- [ ] Kiểm tra helm/compose env vars/flags liên quan events cũ và xoá.
- [ ] Thêm migration note trong CHANGELOG: từ commit/sprint nào chỉ dùng events mới.
- [ ] Viết script cleanup data/queue tồn đọng events cũ trong RabbitMQ trước khi deploy production (ví dụ `rabbitmqadmin purge queue name=<legacy_queue>` và xoá bindings cũ).

