# Video Crawler – Keyframe Extractor PRD

## Objective
Create a production-ready `services/video-crawler/keyframe_extractor` module/service that upgrades the current length-based frame grabbing into a scene-aware extractor powered by PySceneDetect’s `AdaptiveDetector` (see `pyscenedetect_adaptive_detector_guide.md`). The extractor must plug into the existing `VideoProcessor` pipeline, persist frames through `VideoFrameCRUD`, and emit `videos.keyframes.ready*` events that downstream workers already consume.

## Background & Current State
- **Triggering events**: `VideoCrawlerService` subscribes to `videos.search.request`, downloads videos in parallel via platform crawlers, and delegates each asset to `VideoProcessor.process_video`.
- **Storage contracts**: `VideoCRUD` inserts the parent video row; frames are written via `IdempotencyManager.create_frame_with_idempotency` and broadcast through `EventEmitter.publish_videos_keyframes_ready`.
- **Current extractor**: `LengthAdaptiveKeyframeExtractor` (OpenCV only) samples timestamps derived from video length (e.g., `[0.2, 0.5, 0.8]` for short clips). Blur filtering is a simple Laplacian threshold. There is no notion of scene cuts, motion robustness, or adaptive sensitivity. TikTok has a bespoke downloader but still falls back to the same extractor.
- **Observed gaps**
  - Timestamp heuristics miss quick transitions and yield redundant frames on slow videos.
  - Parameters are hard-coded; tuning requires code changes.
  - Extraction is synchronous inside the crawler container, blocking other work and complicating scaling.
  - Limited instrumentation: we only log counts but cannot inspect per-scene metrics.

## Goals & Success Criteria
1. **Scene-aware frames**: Use PySceneDetect `AdaptiveDetector` to pick frame boundaries driven by HSV differences + adaptive deviation (per guide §3) so that each keyframe aligns with a meaningful scene cut.
2. **Configurable sensitivity**: Expose detector knobs (`adaptive_threshold`, `min_scene_len`, `window_width`, `min_content_val`, luma-only) via `config_loader` / env vars so operators can tune without redeploying.
3. **Composable service**: Isolate extractor logic behind a clear async interface (e.g., `KeyframeExtractorInterface.extract_keyframes(...)`) so that `VideoProcessor` can swap implementations or run extraction workers independently.
4. **Idempotent persistence**: Reuse existing CRUD + `IdempotencyManager` to avoid duplicate frame rows when a job replays videos.
5. **Operational transparency**: Emit structured logs/metrics for detector runtime, number of scenes detected, discarded frames (blurred or too short), and downstream event payload sizes.
6. **Compatibility**: Maintain the current events/database schema so existing consumers (`vision-embedding`, `vision-keypoint`, matcher) keep functioning.

## Non-Goals
- Building a UI for reviewing keyframes.
- Changing downstream contracts (`videos.keyframes.ready`, `videos.keyframes.ready.batch` schemas).
- Replacing TikTok’s downloader orchestration (only plug a better extractor under it).
- Video deduplication or advanced motion tracking; focus strictly on frame extraction quality.

## Stakeholders & Users
- **Video crawler team**: Owns ingestion + extraction stages.
- **Vision services**: Depend on high-signal frames for embeddings/keypoints.
- **Matcher/evidence**: Receives better candidate frames, reducing false positives.
- **Ops/SRE**: Requires observability + cleanup hooks due to heavier CPU usage.

## Functional Requirements
- **Input**: Local video path plus metadata (`video_id`, `platform`, optional `duration_s`). Source is `VideoProcessor`, after download completes.
- **Processing**
  - Validate file existence/format (reuse `AbstractKeyframeExtractor.validate_video_file` safeguards).
  - Run PySceneDetect `AdaptiveDetector(...)` over the clip; default parameters per guide section 5A but allow overrides.
  - For each detected scene `(start, end)` pick one or more representative frames:
    - Primary rule: always seek to the temporal midpoint `(start + end) / 2` so that extraction happens in the middle of the shot, not at boundaries.
    - Fallback when a scene is shorter than `FRAME_BUFFER_SECONDS`: use `start.get_seconds()` directly (still avoiding the very beginning if possible).
  - Reject frames whose Laplacian blur score < configurable threshold (default 100, aligned with current config).
  - Persist frames under `{DATA_ROOT}/keyframes/{platform}/{video_id}/...jpg`.
  - Save to DB using existing idempotent helper; ensure final payload mirrors today’s structure (`frame_id`, `ts`, `local_path`).
- **Output**: Return `List[Dict[str, Any]]` to `VideoProcessor`, which then emits `videos.keyframes.ready` and aggregates per batch.
- **Error handling**:
  - If PySceneDetect fails (unsupported codec, etc.), mark the video as failed (include error context) and continue processing other assets; do not fall back to the legacy extractor.
  - Do not crash the service on per-scene failures; log and continue with remaining cuts.
- **Configuration endpoints**:
  - Introduce a single env toggle `KEYFRAME_EXTRACTOR_STRATEGY=pyscene_detect|length_based` (default `pyscene_detect`) to control rollout. Sensitivity knobs (`adaptive_threshold`, `min_scene_len`, `window_width`, `min_content_val`, luma-only) live inside `config_loader` but are not exposed in `.env` yet.
  - Allow overriding output image format/quality as today (`FRAME_FORMAT`, `FRAME_QUALITY`).

## System Architecture
1. **Trigger**: `VideoCrawlHandler` receives `videos.search.request` → `VideoCrawlerService` downloads videos (unchanged).
2. **Extraction worker**:
   - Instantiate `PySceneDetectAdaptiveExtractor` implementing `KeyframeExtractorInterface`.
   - Internally uses PySceneDetect `SceneManager`, `StatsManager` (per guide §6) to detect scenes.
   - Emit structured logs with detector statistics (scene count, thresholds used) for observability; no CSV export requirement.
3. **Persistence layer**: same DB + storage directories defined in `config_loader.VideoCrawlerConfig`.
4. **Events**: same emitter; ensure `publish_videos_keyframes_ready_batch` only fires when we have at least one valid frame.
5. **Cleanup**: `VideoCleanupService` already runs after processing; extend to remove orphaned PySceneDetect stats if debug enabled.

```
videos.search.request
    ↓ (VideoCrawlerService downloads)
VideoProcessor.process_video
    ↓
KeyframeExtractor (PySceneDetect)
    ↓
Frames persisted + events emitted
    ↓
vision-embedding / vision-keypoint
```

## Algorithm & Parameterization
- **Detector**: `AdaptiveDetector` two-pass flow (HSV diff + adaptive deviation). Use the guide’s recommended thresholds:
  - Default balanced: `adaptive_threshold=3.0`, `min_scene_len=15`, `min_content_val=15.0`.
  - Provide presets for “sensitive” (2.0/10/10) and “robust” (4.0/30/20) to match sections 5B/5C.
- **Window width**: Default `2`; tuneable via env.
- **Weights**: start with PySceneDetect defaults; allow optional JSON override for hue/saturation/luma.
- **Scene-to-frame mapping**: config to allow `FRAME_SELECTION_STRATEGY in {midpoint, start, end}`.
- **Default frame location**: the extractor must default to `midpoint`, meaning every detected shot yields a frame from the middle of the segment, aligning with the requirement to avoid boundary frames.
- **Resource control**:
  - Expose `KEYFRAME_MAX_CONCURRENT_EXTRACTIONS` to prevent CPU oversubscription; default derived from CPU count.
  - Streaming support: for large files read sequentially; no full file copy.

## Data Contracts
- **Database**: reuse `videos(video_id, platform, url, duration_s, ...)` and `video_frames(frame_id, video_id, frame_index, timestamp, local_path)`.
- **Events**:
  - `videos.keyframes.ready`: `{ job_id, video_id, platform, frames: [{frame_id, ts, local_path}] }`
  - `videos.keyframes.ready.batch`: `{ job_id, batch: [{video_id, frames:[...]}] }`
  - `videos.collections.completed`: unchanged; still emitted after extraction completes for all videos.
  - `video_keyframes_ready` events from `vision-keypoint` remain downstream responsibilities.

## Operational Considerations
- **Dependencies**: add `scenedetect[opencv]` to `services/video-crawler/requirements.txt`; ensure Docker image bundles ffmpeg.
- **Logging**: Log detector run time, number of cuts, blur rejections, and error states. Use `job_id` and `video_id` for correlation.
- **Metrics**: Add counters (frames per video, % blurred, average scene length). Publish to existing logging pipeline for ingestion.
- **Feature flags**:
  - `KEYFRAME_EXTRACTOR_STRATEGY=pyscene_detect|length_based` (default `pyscene_detect`) for gradual rollout; no other new `.env` knobs initially.
- **Failure modes**:
  - Detector failure on a video → log the error, mark the video as failed, continue handling other videos in the batch.
  - No scenes detected → treat as single scene; ensure at least one frame is emitted unless the video is shorter than 2 seconds.
  - Long videos (>2 minutes) → limit to first N scenes or evenly sample to avoid explosion; configurable `KEYFRAME_MAX_SCENES`.
- **Cleanup**: Extend `VideoCleanupService` to remove orphan frames older than retention; include new directories.

## Testing & Validation
- **Unit tests**: cover detector wrapper (parameter mapping, failure propagation, blur filtering, file validation).
- **Integration tests**: run within `services/video-crawler/tests` using short sample clips to assert DB inserts + events; ensure when `PVM_TEST_MODE=true` extraction can be skipped/mocked.
- **Regression safeguards**: Compare existing `LengthAdaptive` output vs new detector on curated set; ensure equal or higher number of usable frames and no regressions in downstream matching accuracy.

## Milestones
1. Spike: wrap PySceneDetect in a prototype extractor, confirm dependencies build inside Docker image.
2. Integration: wire extractor behind feature flag, update config/env handling, add telemetry.
3. Rollout: enable in staging with `KEYFRAME_EXTRACTOR_STRATEGY=pyscene_detect`, monitor metrics for 1 week, then set as default.

## Open Questions
- Should we store PySceneDetect scene boundaries (start/end) in DB for later evidence building?
- Do we need GPU-aware decoding toggles, or is CPU-only acceptable for expected throughput?
- How many frames per video do downstream models actually need? (May influence `KEYFRAME_MAX_SCENES`.)
- Should TikTok continue using its downloader-managed extraction, or migrate fully to the shared PySceneDetect path once parity is proven?

---
This PRD is grounded in the existing `services/video-crawler` architecture and the PySceneDetect AdaptiveDetector behaviors outlined in `pyscenedetect_adaptive_detector_guide.md`. It aims to clarify the scope, interfaces, and operational expectations before implementation begins.
