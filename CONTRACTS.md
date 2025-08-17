# Event Contracts Specification (Updated)

This document reflects the current, validated JSON Schemas found under `libs/contracts/contracts/schemas`. Handlers validate payloads using `contracts.validator` and topics use dotted routing keys. Underscore schema names map to dotted topic aliases automatically.

## Updated Service Names

- Catalog Collector → Dropship Product Finder
- Media Ingestion → Video Crawler

## Envelope and Validation

- Events are published as plain JSON payloads that match the schemas below. There is no separate payload wrapper.
- The broker enriches messages with a transient `_metadata` object containing `timestamp`, `correlation_id`, and `topic`. Do not rely on `_metadata` for business logic or persistence.
- Several events include a required `event_id` (UUIDv4) for idempotency and tracking; others allow additional fields (`additionalProperties: true`).

## RabbitMQ Routing

- Exchange: `product_video_matching` (type: topic, durable: true)
- Routing keys: dotted names (e.g., `products.collect.request`)
- Queues: declared per-subscriber as `queue.<topic>` and bound to the exchange
- DLQ: messages that exceed retries are republished to a queue named `<queue>.dlq`

## Event Names and Aliases

- Schemas are stored with underscore names (e.g., `image_embeddings_completed`). They are aliased to dotted topic names (e.g., `image.embeddings.completed`). Both forms are accepted by the validator.

## Topics & JSON Schemas

Below are the current topics and their payload schemas (required fields shown explicitly; many schemas allow extra fields).

### products.collect.request (`products_collect_request.json`)

```json
{
  "job_id": "string",
  "top_amz": 1,
  "top_ebay": 5,
  "queries": { "en": ["string", "..."] }
}
```

Notes: `top_amz` and `top_ebay` are integers in [1, 100].

### products.collections.completed (`products_collections_completed.json`)

```json
{ "job_id": "string", "event_id": "uuid" }
```

### products.images.ready.batch (`products_images_ready_batch.json`)

```json
{ "job_id": "string", "event_id": "uuid", "total_images": 0 }
```

### products.image.ready (`products_image_ready.json`)

```json
{
  "product_id": "string",
  "image_id": "string",
  "local_path": "string",
  "metadata": { "width": 0, "height": 0, "format": "string" }
}
```

Note: `additionalProperties` are allowed; publishers may include `job_id` for traceability.

### videos.search.request (`videos_search_request.json`)

```json
{
  "job_id": "string",
  "industry": "string",
  "queries": { "vi": ["string"], "zh": ["string"] },
  "platforms": ["youtube", "bilibili"],
  "recency_days": 30
}
```

### videos.keyframes.ready.batch (`videos_keyframes_ready_batch.json`)

```json
{ "job_id": "string", "event_id": "uuid", "total_keyframes": 0 }
```

### videos.keyframes.ready (`videos_keyframes_ready.json`)

```json
{
  "video_id": "string",
  "frames": [ { "frame_id": "string", "ts": 0.0, "local_path": "string" } ],
  "job_id": "string"
}
```

### videos.collections.completed (`videos_collections_completed.json`)

```json
{ "job_id": "string", "event_id": "uuid" }
```

### products.image.masked (`products_image_masked.json`)

```json
{ "event_id": "uuid", "job_id": "string", "image_id": "string", "mask_path": "string" }
```

### products.images.masked.batch (`products_images_masked_batch.json`)

```json
{ "event_id": "uuid", "job_id": "string", "total_images": 0 }
```

### video.keyframes.masked (`video_keyframes_masked.json`)

```json
{
  "event_id": "uuid",
  "job_id": "string",
  "video_id": "string",
  "frames": [ { "frame_id": "string", "ts": 0.0, "mask_path": "string" } ]
}
```

### video.keyframes.masked.batch (`video_keyframes_masked_batch.json`)

```json
{ "event_id": "uuid", "job_id": "string", "total_keyframes": 0 }
```

### image.embedding.ready (`image_embedding_ready.json`)

```json
{ "job_id": "string", "asset_id": "string", "event_id": "uuid" }
```

### image.embeddings.completed (`image_embeddings_completed.json`)

```json
{
  "job_id": "string",
  "event_id": "uuid",
  "total_assets": 0,
  "processed_assets": 0,
  "failed_assets": 0,
  "has_partial_completion": false,
  "watermark_ttl": 0
}
```

### video.embedding.ready (`video_embedding_ready.json`)

```json
{ "job_id": "string", "asset_id": "string", "event_id": "uuid" }
```

### video.embeddings.completed (`video_embeddings_completed.json`)

```json
{
  "job_id": "string",
  "event_id": "uuid",
  "total_assets": 0,
  "processed_assets": 0,
  "failed_assets": 0,
  "has_partial_completion": false,
  "watermark_ttl": 0
}
```

### image.keypoint.ready (`image_keypoint_ready.json`)

```json
{ "job_id": "string", "asset_id": "string", "event_id": "uuid" }
```

### image.keypoints.completed (`image_keypoints_completed.json`)

```json
{ "job_id": "string", "event_id": "uuid" }
```

### video.keypoint.ready (`video_keypoint_ready.json`)

```json
{ "job_id": "string", "asset_id": "string", "event_id": "uuid" }
```

### video.keypoints.completed (`video_keypoints_completed.json`)

```json
{ "job_id": "string", "event_id": "uuid" }
```

### match.request (`match_request.json`)

```json
{
  "job_id": "string",
  "industry": "string",
  "product_set_id": "string",
  "video_set_id": "string",
  "top_k": 20
}
```

### match.result (`match_result.json`)

```json
{
  "job_id": "string",
  "product_id": "string",
  "video_id": "string",
  "best_pair": { "img_id": "string", "frame_id": "string", "score_pair": 0.0 },
  "score": 0.0,
  "ts": 0.0
}
```

### matchings.process.completed (`matchings_process_completed.json`)

```json
{ "job_id": "string", "event_id": "uuid" }
```

### evidences.generation.completed (`evidences_generation_completed.json`)

```json
{ "job_id": "string", "event_id": "uuid" }
```

### job.completed (`job_completed.json`)

```json
{ "job_id": "string", "...": "additional properties allowed" }
```

## Rules

- Validate all inbound events with the JSON Schemas above.
- IDs are non-empty strings; numeric values follow the types indicated by schemas.
- Schemas permit `additionalProperties: true` to support forward-compatible fields.
## Service Event Map

### main-api

- Publishes: `products.collect.request`, `videos.search.request`, `match.request`, `job.completed`
- Subscribes: `image.embeddings.completed`, `video.embeddings.completed`, `image.keypoints.completed`, `video.keypoints.completed`, `matchings.process.completed`, `evidences.generation.completed`

### dropship-product-finder

- Publishes: `products.collections.completed`, `products.images.ready.batch`, `products.image.ready`
- Subscribes: `products.collect.request`

### video-crawler

- Publishes: `videos.keyframes.ready.batch`, `videos.keyframes.ready`, `videos.collections.completed`
- Subscribes: `videos.search.request`

### product-segmentor

- Publishes: `products.image.masked`, `products.images.masked.batch`, `video.keyframes.masked`, `video.keyframes.masked.batch`
- Subscribes: `products.images.ready.batch`, `products.image.ready`, `videos.keyframes.ready.batch`, `videos.keyframes.ready`

Note: Some internal completion events like `products.images.masked.completed` and `video.keyframes.masked.completed` may be emitted for observability; no JSON Schemas are defined for these in `libs/contracts`.

### vision-embedding

- Publishes: `image.embedding.ready`, `image.embeddings.completed`, `video.embedding.ready`, `video.embeddings.completed`
- Subscribes: `products.images.masked.batch`, `products.image.masked`, `video.keyframes.masked.batch`, `video.keyframes.masked`

### vision-keypoint

- Publishes: `image.keypoint.ready`, `image.keypoints.completed`, `video.keypoint.ready`, `video.keypoints.completed`
- Subscribes: `products.images.masked.batch`, `products.image.masked`, `video.keyframes.masked.batch`, `video.keyframes.masked`

### matcher

- Publishes: `match.result`, `matchings.process.completed`
- Subscribes: `match.request`

### evidence-builder

- Publishes: `evidences.generation.completed`
- Subscribes: `match.result`, `matchings.process.completed`


### results-api

- Publishes: —
- Subscribes: — (exposes REST endpoints for reads only)
