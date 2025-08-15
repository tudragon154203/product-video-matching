# Sprint 6.3: Single-job completion for Videos (batch pre-announce + per-frame processing)

## Scope & Goal
Eliminate duplicate `video.embeddings.completed` and `video.keypoints.completed` events for the **same job_id** by (1) broadcasting an **up-front batch count** of expected frames, (2) having both vision services track counts against that batch, and (3) consuming the same topic on **separate queues** (one per service) to avoid cross-consumer interference.  
**Goal:** exactly **one** `*.completed` per job/service per job_id.

## Contracts (authoritative)
- **Use** `libs/contracts/contracts/schemas/videos_keyframes_ready_batch.json` as the **job-level pre-announce**. (Exists in repo.)
- Keep existing per-asset `videos.keyframes.ready` (per video_id with `frames[]`) as is; batch must arrive **first** to set `expected_total_frames`.

## Required Producer Change (video-crawler)
1. **Publish order**
   - Emit **`videos.keyframes.ready.batch`** once per job **before** any `videos.keyframes.ready`.
   - Payload (align to schema):  
     `{ "job_id": "<job>", "event_id": "<uuid4>", "total_frames": <int> }`
2. **Implement**
   - In `services/video-crawler/services/service.py`: compute **sum of frames** across all candidate videos for the job; **publish** the batch event, then stream the usual `videos.keyframes.ready` (per video) events.

## Required Consumer Changes (vision-embedding & vision-keypoint)
1. **Different queues to the same exchange**
   - Ensure **distinct queue names** when subscribing so both services receive the same topic independently:
     - Embedding: `queue_name="q.vision_embedding.keyframes.batch"`
     - Keypoint: `queue_name="q.vision_keypoint.keyframes.batch"`
2. **Subscribe to the batch topic**
   - Add a new handler for **`videos.keyframes.ready.batch`** in both services. On receipt:
     - Set `job_tracking[job_id].expected = total_frames`
     - Start/refresh the watermark timer.
3. **Use batch count when per-video frames arrive**
   - Replace per-video frame count with **batch-stored** expected total for the **job**, not per video.
4. **Completion publishing guard**
   - Only publish `video.embeddings.completed` / `video.keypoints.completed` when `done >= expected` **and** we haven’t emitted for this job yet (use a per-job idempotency set).

## Handlers & Validation
- Add validators and handlers:
  - **Embedding**
    - `@validate_event("videos_keyframes_ready_batch")`
    - `handle_videos_keyframes_ready_batch(event)`
  - **Keypoint**
    - `@validate_event("videos_keyframes_ready_batch")`
    - `handle_videos_keyframes_ready_batch(event)`

## Messaging Details (unchanged except queue names)
- Each service binds its **own** durable queue to the **same** routing key.

## Implementation Checklist
**Contracts**
- [ ] Ensure `videos_keyframes_ready_batch.json` is exported in `contracts.validator` map.

**video-crawler**
- [ ] Compute `total_frames` across planned downloads/extractions.
- [ ] Publish `videos.keyframes.ready.batch` **once** per job prior to streaming `videos.keyframes.ready`.

**vision-embedding**
- [ ] New subscription: `videos.keyframes.ready.batch` (queue `q.vision_embedding.keyframes.batch`).
- [ ] Store `expected_total_frames[job_id]=total_frames`.
- [ ] `handle_videos_keyframes_ready`: always read `expected_total_frames[job_id]`.
- [ ] Emit **one** `video.embeddings.completed` guarded by an idempotent flag.

**vision-keypoint**
- [ ] Same as embedding but for keypoints path.
- [ ] Emit **one** `video.keypoints.completed` guarded by an idempotent flag.

**Broker Wiring**
- [ ] Use explicit `queue_name` for both services’ subscriptions.

**Tests**
- [ ] Unit: handler sets `expected_total_frames` on batch; ignores duplicates.
- [ ] Integration: send batch(100) → 100 per-asset frames → expect **exactly one** `*.completed` per service.
- [ ] Integration: batch(100) → send 60 frames → watermark timeout → expect `has_partial_completion=true`.
- [ ] E2E smoke: no duplicate phase events; counts match API/DB.

## Acceptance Criteria
1. For any job with N frames:
   - Exactly **one** `video.embeddings.completed` and **one** `video.keypoints.completed`.
   - `processed_assets == N` and `total_assets == N` in completed payload; partials on timeout include `has_partial_completion=true`.
2. Both services consume from **their own queues** and do **not** steal messages from each other.
3. No duplicate phase events for a single job in main-api logs/tests.

---

### Notes
- Embedding service already emits per-asset `video.embedding.ready` and updates progress per frame; job-level expected must now be **batch-driven**.
- The broker wrapper supports `queue_name`; use this to separate consumers cleanly.
