# Event Contracts Specification

## 1. Standard Envelope

All pub/sub events follow this JSON envelope structure:

```json
{
  "event_id": "uuid-v4",
  "schema_version": "v1",
  "type": "<topic-name>",
  "source": "<service-name>",
  "occurred_at": "ISO8601",
  "trace": {
    "job_id": "...",
    "parent_event_id": "..."
  },
  "payload": {
    ...
  }
}
```

## 2. RabbitMQ Routing

- Exchange: `events` (type: topic, durable: true)
- Queue: Each service has its own queue, with binding key per topic
- DLQ: `<queue>.dlq` with TTL retry 5m → requeue
- Events are validated before processing (JSON Schema)

## 3. Topics & JSON Schemas

### 3.1 products.collect.request

```json
{
  "job_id": "string",
  "industry": "string",
  "top_amz": "integer",
  "top_ebay": "integer"
}
```

### 3.2 products.images.ready

```json
{
  "product_id": "string",
  "image_id": "string",
  "local_path": "string"
}
```

### 3.3 videos.search.request

```json
{
  "job_id": "string",
  "industry": "string",
  "queries": ["string"],
  "platforms": ["youtube", "bilibili"],
  "recency_days": "integer"
}
```

### 3.4 videos.keyframes.ready

```json
{
  "video_id": "string",
  "frames": [
    {
      "frame_id": "string",
      "ts": "float",
      "local_path": "string"
    }
  ]
}
```

### 3.5 features.ready

```json
{
  "entity_type": "product_image|video_frame",
  "id": "string",
  "emb_rgb": ["float"],
  "emb_gray": ["float"],
  "kp_blob_path": "string"
}
```

### 3.6 match.request

```json
{
  "job_id": "string",
  "industry": "string",
  "product_set_id": "string",
  "video_set_id": "string",
  "top_k": "integer"
}
```

### 3.7 match.result

```json
{
  "job_id": "string",
  "product_id": "string",
  "video_id": "string",
  "best_pair": {
    "product_img": "string",
    "video_frame": "string"
  },
  "score": "float",
  "ts": "float"
}
```

### 3.8 match.result.enriched

```json
{
  "job_id": "string",
  "product_id": "string",
  "video_id": "string",
  "best_pair": {
    "product_img": "string",
    "video_frame": "string"
  },
  "score": "float",
  "ts": "float",
  "evidence_path": "string"
}
```

## 4. Rules

- Validate before publishing/subscribing
- Increment schema version when making breaking changes
- All IDs are non-empty strings
- All floats have ≤ 6 decimal places
- Payloads are ≤ 1MB (to avoid overloading the bus)