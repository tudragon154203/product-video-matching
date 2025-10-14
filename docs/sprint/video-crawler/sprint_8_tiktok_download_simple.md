# Sprint 8: TikTok Download Simple Strategy (TikWM)

## Overview
- Add a lightweight TikTok download path that hits TikWM's public media endpoint (`https://www.tikwm.com/video/media/play/{video_id}.mp4`) without depending on the Scrapling API service.
- Keep the existing pluggable strategy architecture (`platform_crawler/tiktok/download_strategies/`) so operators can select `tikwm`, `scrapling-api`, or `yt-dlp` via configuration.
- Ensure the new path streams files into the same storage layout, reuses keyframe extraction, and emits comparable logs/metrics.
- Document rollout guardrails so the team can trial TikWM in staging before enabling it broadly.

## Current State
- `services/video-crawler/platform_crawler/tiktok/tiktok_downloader.py` delegates downloads to a strategy instance built by `TikTokDownloadStrategyFactory`.
- Available strategies today:
  - `YtdlpDownloadStrategy` (`platform_crawler/tiktok/download_strategies/ytdlp_strategy.py`) — shelling out to `yt_dlp`.
  - `ScraplingApiDownloadStrategy` (`platform_crawler/tiktok/download_strategies/scrapling_api_strategy.py`) — calls `/tiktok/download` via `TikTokDownloadClient`.
- Strategy selection defaults to `scrapling-api` through `config_loader.py:TIKTOK_DOWNLOAD_STRATEGY`.
- Metrics and logging for download attempts are centralized in `platform_crawler/tiktok/metrics.py`.
- Unit coverage around strategies lives in `services/video-crawler/tests/unit/tiktok/test_tiktok_download_strategies.py`.
- Demo script `services/video-crawler/demo/tiktok_download_tikwm_ok.py` proves TikWM can return direct MP4 assets after a simple regex + HEAD check.

## Goals & Success Criteria
- **Primary**: When `TIKTOK_DOWNLOAD_STRATEGY=tikwm`, the crawler downloads MP4s directly from TikWM, saves them under the configured TikTok video directory, and continues through keyframe extraction.
- **Parity**: Strategy swap does not break existing Scrapling or `yt-dlp` flows; factory/registry continue to work with previous values.
- **Reliability**: Validate content type/size, handle redirects, and provide clear error codes so operators can fall back if TikWM throttles or changes formats.
- **Observability**: Logs and metrics identify the `tikwm` strategy and track counts, timings, and error classes in line with other strategies.
- **Rollout-ready**: Toggle-able via env vars, with documentation and tests that derisk enabling TikWM in staging.

## Scope
- In-scope: new strategy implementation, configuration updates, metrics/logging extensions, documentation, and unit/integration tests.
- Out-of-scope: core TikTok search flow, changes to Scrapling API client, introducing new external services, or modifying downstream pipelines that consume downloaded files.

## Architecture & Design

### Strategy Registration
- Create `platform_crawler/tiktok/download_strategies/tikwm_strategy.py` implementing `TikTokDownloadStrategy`.
- Wire the new class directly into `TikTokDownloadStrategyFactory` / `TikTokDownloadStrategyRegistry` without expanding `download_strategies/__init__.py`, keeping that module untouched.
- Update `TikTokDownloadStrategyFactory.create_strategy` to accept `tikwm`, and register it in `TikTokDownloadStrategyRegistry`.
- Add `tikwm` as a documented enum value for `TIKTOK_DOWNLOAD_STRATEGY` in `config_loader.py` and `services/video-crawler/README.md`.

### TikWM Download Flow
- Core steps (adapted from the demo):
  1. Extract the numeric video ID from the TikTok URL via regex; log and abort if the pattern is not matched.
  2. Build the TikWM media URL using the fixed base `https://www.tikwm.com/video/media/play/{video_id}.mp4` (no new env overrides required).
  3. Issue a HEAD request (`httpx.AsyncClient().head(...)`) to resolve redirects and confirm the final URL plus response headers; capture the final URL for download.
  4. Validate `Content-Type` starts with `video/` and `Content-Length` (if provided) is below the existing 500 MB guardrail.
  5. Stream the MP4 to disk in chunks (8 KB) while monitoring size and aborting on overage or network errors.
- Prefer `httpx.AsyncClient` for consistency with the Scrapling strategy; the synchronous strategy interface can wrap async calls using the existing event-loop detection pattern.
- Ensure the synchronous `download_video` method remains drop-in for `download_videos_batch` parallelism: reuse the same "detect running loop → run async helper in thread" approach so multiple TikWM downloads can execute concurrently under the existing semaphore.
- Store downloads under `{video_id}.mp4` inside `self.video_storage_path`, matching current cleanup jobs and tests.

### Keyframe Extraction
- Reuse the shared extraction flow:
  - Factor the common logic in `ytdlp_strategy.py` / `scrapling_api_strategy.py` into a helper (e.g., `extract_keyframes_common(...)`) or keep a small duplication block but ensure the new strategy mirrors the retry + cleanup semantics.
  - Continue writing keyframes to `config["keyframe_storage_path"]/{video_id}` and returning `(keyframes_dir, List[Tuple[timestamp, path]])`.

### Metrics & Logging
- Call `record_download_metrics(strategy="tikwm", ...)` in both success and failure paths, including:
  - `execution_time`: overall wall-clock duration of the download function.
  - `file_size`: final file size if the download succeeds.
  - `error_code`: descriptive codes such as `NO_VIDEO_ID`, `HEAD_FAILED`, `INVALID_CONTENT_TYPE`, `STREAM_ERROR`, or `SIZE_LIMIT_EXCEEDED`.
  - `retries`: count TikWM retry attempts (see below).
- Emit structured log entries (via `configure_logging`) indicating start, HEAD resolution, streaming progress milestones, and final status.

### Error Handling & Retries
- Provide a small retry envelope (e.g., up to 2 attempts) for transient HTTP failures:
  - Retry on 5xx or network exceptions with backoff (similar to `yt_dlp` strategy).
  - Fail fast on deterministic errors (missing video ID, 404/403, invalid content type).
- On partial downloads, ensure the temp file is removed to avoid confusing downstream processors.
- Consider optional fallback:
  - Config flag `TIKWM_FALLBACK_STRATEGY` (default `scrapling-api`) allowing the TikWM strategy to delegate to another registered strategy on consistent failures; decide during implementation if we keep logic within strategy or rely on operators to change `TIKTOK_DOWNLOAD_STRATEGY`.

### Configuration
- Reuse existing strategy config shape—hardcode TikWM defaults inside the strategy (base URL, timeout, size cap) so no new env vars or config keys are necessary.
- Continue passing the existing `strategy_config` copy from `TikTokDownloader.__init__`, allowing reuse of global options like `retries` and `timeout`.

### Storage & Permissions
- No schema changes: downloads continue under `tempfile.gettempdir()/videos/tiktok` or configured override.
- Confirm file permissions match existing logic (open in binary write mode, rely on OS defaults).
- Continue to emit `local_path` in the download result dictionary for downstream services.

## Implementation Plan
1. Scaffold `TikwmDownloadStrategy` with configuration wiring, logging, and placeholders for HEAD + stream helpers.
2. Introduce regex helper for video ID extraction (unit-test separately); consider colocating in `tikwm_strategy.py` or a shared utility if future reuse is expected.
3. Implement HEAD resolution and streaming download with validations and retries.
4. Reuse/extract keyframe helper to avoid duplication.
5. Update `factory.py`, `__init__.py`, and `TikTokDownloadStrategyRegistry` to recognize `tikwm`; default remains `scrapling-api`.
6. Extend `config_loader.py` and README/environment docs with new configuration knobs.
7. Capture metrics/logging parity, including new error code constants.
8. Add/extend unit tests:
   - Strategy factory selects TikWM for new env value.
   - TikWM strategy handles success path, invalid URLs, HEAD failures, oversized files, and retry exhaustion (mock `httpx`).
   - Keyframe extraction path invoked and cleans up on failure.
9. (Optional) Integration test leveraging `respx`/`pytest-httpx` to simulate TikWM responses and assert file creation + metrics.
10. Update `docs/sprint/video-crawler/tiktok-download-guide.md` or README with TikWM troubleshooting notes.

## Testing Strategy
- **Unit**: Mock `httpx.AsyncClient` to cover:
  - Successful HEAD + GET sequence.
  - Redirect handling (`response.is_redirect` / `response.headers["Location"]`).
  - Non-video content type and oversize responses.
  - Network exceptions to verify retry/backoff and cleanup.
- **Integration (optional but recommended)**: Run crawler against a fake TikWM server (FastAPI or `pytest-httpserver`) to confirm end-to-end flow from `TikTokDownloader.download_videos_batch`.
- **Regression**: Re-run existing TikTok download tests to ensure other strategies remain unaffected.
- **Manual**: Use the demo script as smoke (`python services/video-crawler/demo/tiktok_download_tikwm_ok.py`) and then exercise the crawler with `TIKTOK_DOWNLOAD_STRATEGY=tikwm`.

## Rollout Plan
- Land code with `TIKTOK_DOWNLOAD_STRATEGY` default unchanged (`scrapling-api`).
- Deploy to staging, toggle `tikwm` for a subset of jobs, monitor metrics/logs for success rates and failures.
- Decide fallback strategy (switch back to `scrapling-api` or `yt-dlp`) if TikWM error rates spike.
- Once stable, enable `tikwm` in production via env var; keep feature flag to revert quickly.

## Risks & Mitigations
- **TikWM API changes or throttling**: Mitigate by adding clear error codes, retry/backoff, and documenting fallback toggle.
- **Content-type drift (non-MP4 responses)**: Enforce validation and treat mismatch as fatal to avoid polluting storage.
- **Rate limiting**: Consider introducing a semaphore or configurable concurrency limit specific to TikWM if needed.
- **Legal / Terms-of-service alignment**: Confirm this public endpoint is acceptable for production use before rollout.
- **Duplicate logic proliferation**: Extract shared helpers (keyframe extraction, retry wrappers) to keep maintenance tractable.

## Open Questions
- Should TikWM errors automatically cascade into a configured fallback strategy, or should operators flip the env var manually?
- Do we need to rotate TikWM base URLs (mirrors) to avoid regional blocking?
- Are there known regional restrictions requiring proxy support for TikWM requests (reuse existing proxy settings or add new config)?
- Is staging allowed to hit TikWM directly, or do we need a mock service for non-production environments?
- Should we persist TikWM response metadata (e.g., redirect target) for debugging/auditing?
