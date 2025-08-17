---
inclusion: fileMatch
fileMatchPattern: '*event*|*contract*|*schema*'
---

# Event Contracts & Messaging

## Event Structure
All events must follow the standard envelope format:
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
  "payload": { ... }
}
```

## Key Event Types
- `products.collect.request` → Trigger product collection
- `products.image.ready` → Product images available
- `videos.search.request` → Trigger video search
- `videos.keyframes.ready` → Video frames extracted
- `features.ready` → Embeddings/keypoints computed
- `match.request` → Start matching process
- `match.result` → Raw matching results
- `match.result.enriched` → Results with evidence

## Validation Rules
- **Schema Validation**: Validate against JSON schemas in `libs/contracts`
- **Payload Size**: Keep payloads ≤ 1MB to avoid bus overload
- **Required Fields**: All envelope fields are mandatory
- **ID Format**: Use UUID v4 for all IDs

## RabbitMQ Configuration
- **Exchange**: `events` (topic, durable)
- **Queues**: Service-specific with appropriate bindings
- **DLQ**: Dead letter queues with 5-minute TTL retry
- **Durability**: All queues and messages are durable

## Error Handling
- **Validation Errors**: Reject invalid events immediately
- **Processing Errors**: Send to DLQ for retry
- **Poison Messages**: Manual intervention after max retries
- **Monitoring**: Track event processing metrics

## Tracing & Debugging
- **Job Tracing**: Include `job_id` in all related events
- **Parent Tracking**: Link events with `parent_event_id`
- **Timestamps**: Use ISO8601 format for all timestamps
- **Correlation**: Enable end-to-end request tracing