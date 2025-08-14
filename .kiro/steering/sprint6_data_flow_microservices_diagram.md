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

- Mỗi `.completed` bắt buộc có `job_id` và `event_id` (UUIDv7) để Phase Manager quản lý và tránh trùng.
- Các sự kiện `ready` là **per_asset** (theo từng ảnh hoặc keyframe), còn các `.completed` là **per_jobs**.
- Phase Manager chỉ dựa trên `.completed` để chuyển pha.
- Song song được đồng bộ bằng **barrier**: chỉ khi đủ event mới sang pha mới.
- Đã bỏ `match.result.enriched` để tránh nhầm với `match.result`.
- Loại bỏ hoàn toàn `features.extraction.completed` vì đã thay bằng các `.completed` cụ thể hơn.

## Danh sách events

- `products.collections.completed`
- `videos.collections.completed`
- `image.embedding.ready` (per_asset)
- `image.embeddings.completed` (per_jobs)
- `image.keypoint.ready` (per_asset)
- `image.keypoints.completed` (per_jobs)
- `video.embedding.ready` (per_asset)
- `video.embeddings.completed` (per_jobs)
- `video.keypoint.ready` (per_asset)
- `video.keypoints.completed` (per_jobs)
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
  "event_id": "uuidv7"
}
```

**Per-jobs:**
```json
{
  "job_id": "string",
  "event_id": "uuidv7"
}
```

## Dư thừa từ hệ thống cũ sau khi áp dụng mới

- `features.extraction.completed` → Bỏ hẳn, đã tách thành `*.embeddings.completed` và `*.keypoints.completed`.
- `match.result.enriched` → Bỏ, tránh trùng với `match.result`.
- Các event `.completed` không chứa `job_id` → Bỏ hoặc sửa lại để đúng format.
- Các trạng thái trung gian không dùng trong phase management → Chỉ giữ nếu còn giá trị debug hoặc logging.

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
- [ ] Viết script cleanup data/queue tồn đọng events cũ trong RabbitMQ trước khi deploy production.

