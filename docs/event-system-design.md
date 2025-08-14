# Event Processing System Design (Sprint 6)

## Overview
The new event system processes assets at the individual level while maintaining job-level tracking entirely within VisionServices. MainAPI only receives completed events to trigger phase transitions.

## Key Components
1. **Per-Asset Events** (handled internally by VisionServices):
   - `image.embedding.ready`
   - `video.embedding.ready`
   - `image.keypoint.ready`
   - `video.keypoint.ready`
   - Corresponding `.processed` events

2. **Completed Events** (published to MainAPI):
   - `image.embeddings.completed`
   - `video.embeddings.completed`
   - `image.keypoints.completed`
   - `video.keypoints.completed`

## Event Payloads
```json
// READY Event
{
  "event_id": "uuid",
  "job_id": "job123",
  "asset_id": "img456",
  "timestamp": "2023-01-01T00:00:00Z",
  "asset_type": "image",
  "processing_stage": "embedding",
  "local_path": "/path/to/asset.jpg"
}

// COMPLETED Event
{
  "job_id": "job123",
  "event_type": "embeddings",
  "total_assets": 100,
  "processed_assets": 95,
  "failed_assets": 5,
  "has_partial_completion": true,
  "watermark_ttl": 300
}
```

## VisionService Implementation
- **State Tracking**: Uses Redis to store:
  ```python
  {
    "job123": {
      "expected_images": 50,
      "expected_frames": 50,
      "embeddings_done": 95,
      "keypoints_done": 80,
      "timer": "active"
    }
  }
  ```
- **Watermark Timer**: Starts on first asset receipt, publishes COMPLETED on timeout
- **Idempotency**: Checks Redis for existing event_id before processing

## Integration Points
![Event Flow Diagram](event-flow.md)

For detailed sequence flow, see [Event Flow Diagram](event-flow.md).

## Edge Cases
1. **Zero Assets**: Immediate COMPLETED event with zero counts
2. **Timeouts**: Partial COMPLETED event after TTL expiration
3. **Duplicates**: Redis-based event_id deduplication
4. **Failures**: Error counting in COMPLETED events