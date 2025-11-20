# Video Crawler – Sprint 9 PySceneDetect Keyframe Extractor PRD

## Objective
Ship a new PySceneDetect-backed keyframe extractor that lives beside (not inside) the existing length-based extractor. The new class must inherit from `services/video-crawler/keyframe_extractor/abstract_extractor.py` and emit the same persistence/events contracts while extracting frames at the middle of each detected scene cut. No fallback to the legacy strategy occurs once `pyscene_detect` is selected.

## Background & Problem Statement
- The current `LengthAdaptiveKeyframeExtractor` samples timestamps purely from video duration percentages. It often misses fast transitions and over-samples uninformative frames on slow scenes.
- Blur filtering is simplistic and cannot leverage scene-level context, causing redundant frames to enter downstream services (`vision-embedding`, `vision-keypoint`, matcher).
- Operators need a drop-in, configurable alternative that can be enabled per environment without code changes.
- Prior exploration (`pyscenedetect_adaptive_detector_guide.md`) validated PySceneDetect’s `AdaptiveDetector` as the right building block, but no productized extractor exists.

## Goals & Success Criteria
1. **Dedicated class**: Introduce `PySceneDetectKeyframeExtractor(AbstractKeyframeExtractor)` in `services/video-crawler/keyframe_extractor/pyscene_detect_extractor.py`. The legacy length-based extractor stays untouched.
2. **Scene-aware midpoints**: Detect scene boundaries via PySceneDetect AdaptiveDetector and always capture a frame at each scene’s temporal midpoint `(start + end) / 2`. Only use `start` when the scene is shorter than the seek buffer.
3. **Single strategy default**: PySceneDetect replaces the old length-based path and ships as the default; no runtime env toggle is required or supported.
4. **Config isolation**: Sensitivity knobs (`adaptive_threshold`, `min_scene_len`, `window_width`, `min_content_val`, `weights_luma_only`) remain inside `config_loader`; they can be tuned internally without surfacing `.env` entries yet.
5. **Parity contracts**: Persist frames via `VideoFrameCRUD`/`IdempotencyManager` and emit the same `videos.keyframes.ready` events so downstream services remain unaware of the strategy swap.
6. **Operational clarity**: Provide structured logs/metrics for detector runtime, scene counts, accepted/dropped frames, and ensure errors mark a video as failed without triggering a fallback.

## Non-Goals
- No refactor of the length-based extractor beyond sharing abstractions.
- No fallback chain or automatic retries to other strategies when PySceneDetect fails; the video is simply marked failed.
- No additional performance benchmark suite; standard regression runs suffice.
- No UI or visualization work.

## Functional Requirements
- **Inputs**: Local file path, `video_id`, `job_id`, platform metadata provided by `VideoProcessor`.
- **Processing flow**:
  1. Validate video file via inherited helper (`validate_video_file`).
  2. Instantiate PySceneDetect `SceneManager` + `StatsManager` + `AdaptiveDetector` using config loader defaults derived from the adaptive detector guide.
  3. Call `scene_manager.detect_scenes(video=path)`.
  4. For every scene `(start_time, end_time)`:
     - Compute `duration = end - start`; `mid_ts = start + duration / 2`.
     - If `duration < MIN_SCENE_DURATION_SECONDS`, clamp to `start + min(duration/2, FALLBACK_OFFSET_SECONDS)` but never before `start + 0.15s` to avoid capturing transition frames.
     - Seek the frame at `mid_ts`, extract via OpenCV, run Laplacian blur filter (same threshold as today, default 100), and skip frames failing the blur threshold.
  5. Persist files under `{DATA_ROOT}/keyframes/{platform}/{video_id}/{scene_index}.jpg` using base class helpers and write DB rows via `VideoFrameCRUD` with idempotency.
  6. Return the resulting payload list to `VideoProcessor` for event emission.
- **Outputs**: Identical payload shape as existing extractor (`frame_id`, `timestamp_seconds`, `local_path`, optional metadata such as `scene_index`).
- **Error handling**: Failure within PySceneDetect raises `KeyframeExtractionError`, causing the video to be marked failed; processing of other videos continues. Individual scene decoding failures are logged and skipped.

## Proposed Solution & Architecture
```
VideoProcessor.process_video
    ↓ (router builder returns codec-aware extractor; no env toggle)
PySceneDetectKeyframeExtractor.extract_keyframes
    ↓ PySceneDetect SceneManager + AdaptiveDetector
Scene list → midpoint timestamps → frame decode → blur filter
    ↓
VideoFrameCRUD / IdempotencyManager
    ↓
EventEmitter.publish_videos_keyframes_ready(+batch)
```

### Key Components
1. **PySceneDetectKeyframeExtractor**
   - Resides in `services/video-crawler/keyframe_extractor/pyscene_detect_extractor.py`.
   - Implements `extract_keyframes(self, ctx: KeyframeExtractionContext) -> ExtractResult` using inherited helpers for IO, file naming, blur scoring, and error construction.
   - Maintains private method `_detect_scenes(Path) -> list[SceneInfo]` for unit testing.

2. **Router wiring**
   - `services/video-crawler/keyframe_extractor/router.py` exposes a builder that returns a codec-aware router combining PySceneDetect and PyAV extractors.
   - Selection is automatic; there is no env toggle to swap strategies.

3. **Config loader updates**
   - Remove the `keyframe_extractor_strategy` toggle. PySceneDetect tuning parameters stay as internal config fields (sourced from config files or secrets).
   - No `.env` entries remain for switching extractor implementations.

4. **Dependencies**
   - Ensure `services/video-crawler/requirements.txt` includes `scenedetect[opencv]` and Docker image bundles ffmpeg.

## Detailed Behavior
- **Scene detection**: Use AdaptiveDetector defaults from the guide (`adaptive_threshold=3.0`, `min_scene_len=15`, `window_width=2`, `min_content_val=15.0`, `weights_luma_only=True`). Allow overrides via config loader for future tuning.
- **Midpoint extraction**: All frames are captured at midpoints. Requirement explicitly forbids capturing at shot start unless the scene is too short to allow a midpoint offset.
- **Throughput control**: Reuse existing worker pool; no new concurrency flags. Extraction runs synchronously within `VideoProcessor` just like today.
- **Instrumentation**:
  - Log per-video line: `job_id`, `video_id`, `scene_count`, `keyframes_saved`, `keyframes_dropped_blur`, `strategy`.
  - Emit metrics through existing observability hooks; since we removed `KEYFRAME_DEBUG_METRICS`, logging is always on at INFO level for aggregate stats, DEBUG for per-scene details if needed.
- **No fallback**: If PySceneDetect extraction fails, there is no automatic retry with the legacy strategy. Operators can revert by redeploying with the legacy extractor but not dynamically per video.

## Data Contracts
- **Database**: Continue writing to `video_frames` table (`frame_id`, `video_id`, `frame_index`, `timestamp`, `local_path`). Optionally store `scene_index` within the JSON metadata blob if available.
- **Events**: `videos.keyframes.ready` and `.batch` payloads remain identical, ensuring downstream services require no changes.

## Operational Plan
- **Rollout**: Default remains PySceneDetect; staging uses PySceneDetect immediately. Rolling back requires reverting to the legacy extractor via code/deploy change rather than an env toggle.
- **Monitoring**: Track average scene count per video and compare with historical length-based frame counts. Alert if scene count is zero for more than X% of videos.
- **Failure handling**: When PySceneDetect raises due to codec or corrupt media, log error, mark video failed, and continue processing other jobs. Operators can inspect logs via Kibana; no special fallback path.
- **Cleanup**: Existing cleanup jobs continue deleting orphaned frames. No additional state besides frames is written.
- **Testing**: Focus on unit tests for the extractor wrapper and limited integration runs inside `services/video-crawler/tests` using short fixtures. No dedicated performance benchmarking this sprint (per guidance).

## Unit Test Plan
- **Scene detection plumbing**: Mock PySceneDetect classes to assert `PySceneDetectKeyframeExtractor` converts detector scenes into midpoint timestamps and skips empty scene lists.
- **Timestamp fallback logic**: Provide synthetic scenes shorter than the minimum duration to ensure we clamp to `start + offset` instead of the boundary.
- **Blur filtering**: Feed deterministic frame matrices (sharp vs blurred) through the inherited Laplacian helper to confirm acceptance/rejection paths.
- **Persistence contract**: Use in-memory/tmp directories to verify files are written to the expected `{platform}/{video_id}` structure and DB payloads contain `frame_index`, `timestamp`, `scene_index` metadata.
- **Error propagation**: Simulate missing files or detector exceptions and assert a `KeyframeExtractionError` is raised without invoking any fallback strategy.

## Milestones
1. **Design sign-off** – finalize this PRD and confirm parameter defaults.
2. **Implementation** – add new extractor class, router wiring, config loader updates, requirements, and documentation.
3. **Validation** – run crawler against smoke dataset; verify midpoint timestamps, scene counts, and event payloads. Document rollback procedure (redeploy with the legacy extractor if needed).
4. **Rollout** – enable PySceneDetect in staging for 48h, then in production upon stable metrics.

## Open Questions
1. Should we persist scene metadata (start/end/midpoint) alongside frame rows for future debugging or evidence builder use?
2. Do we need per-platform overrides for detector sensitivity (e.g., TikTok vs YouTube), or is a global config sufficient initially?
3. Are additional blur heuristics (exposure, motion) required before GA, or can they follow in a later sprint?

---
Reference: `docs/sprint/video-crawler/pyscenedetect_adaptive_detector_guide.md` for detector theory, tuning guidelines, and sample parameter sets.
