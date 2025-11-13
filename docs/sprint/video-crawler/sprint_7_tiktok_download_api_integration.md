# Sprint 7: TikTok Download API Integration

## Overview
- Add a second TikTok download strategy that delegates to the `/tiktok/download` HTTP endpoint documented in `docs/sprint/video-crawler/tiktok-download-guide.md`.
- Keep the existing `yt_dlp` path available as an alternative strategy selected via configuration.
- Ensure `/tiktok/download` requests are fanned out in parallel so batch jobs do not serialize on this long-running call.
- Ensure downloaded assets continue to flow through keyframe extraction and message emission without breaking existing storage layout.

## Current State
- `services/video-crawler/platform_crawler/tiktok/tiktok_crawler.py` instantiates `TikTokDownloader` and calls `download_videos_batch` to pull media after search.
- `TikTokDownloader` in `services/video-crawler/platform_crawler/tiktok/tiktok_downloader.py` downloads videos with `yt_dlp` and immediately extracts keyframes through `extract_keyframes`.
- The crawler already uses `config.TIKTOK_CRAWL_HOST` and `config.TIKTOK_CRAWL_HOST_PORT` for the search API (`TikTokSearcher`), so networking foundations exist.
- No abstraction exists for switching download strategies; tests in `services/video-crawler/tests` import `TikTokDownloader` directly.

## Goals & Success Criteria
- **Primary**: When `TIKTOK_DOWNLOAD_STRATEGY=scrapling-api`, the service retrieves the TikTok media via `/tiktok/download`, stores the MP4, and continues the pipeline.
- **Parity**: Continue supporting the existing `yt_dlp` strategy when `TIKTOK_DOWNLOAD_STRATEGY=yt-dlp`.
- **Observability**: Structured logs and metrics differentiate strategies and include API response metadata (`execution_time`, `error_code`).
- **Backward compatibility**: Default behaviour remains unchanged (`yt-dlp`), all existing unit/integration tests continue to pass.

## Scope
- In-scope: Configuration, downloader refactor, API client, networking retries, download storage, logging/metrics, automated tests, documentation.
- Out-of-scope: Changes to the external TikTok download service, major schema changes in downstream consumers, large-scale refactors of search.

## Architecture & Design

### Strategy Selection Layer
- Introduce a lightweight strategy interface (e.g., `TikTokDownloadStrategy`) inside `tiktok_downloader.py` to encapsulate `download_video` + `extract_keyframes` orchestration.
- Register two strategies:
  - `YtDlpDownloadStrategy` — wraps current logic (move existing code here).
  - `ScraplingApiDownloadStrategy` — new implementation backed by `/tiktok/download`.
- Update `TikTokDownloader` to pick the strategy at runtime via `config.TIKTOK_DOWNLOAD_STRATEGY` (default `yt-dlp`). Allow overrides when constructing the downloader (useful for tests).

### API Client
- Add `TikTokDownloadClient` under `platform_crawler/tiktok/` that uses `httpx.AsyncClient` to call `POST /tiktok/download` (`tiktok-download-guide.md` outlines payload, error codes, retry guidance).
- Request body: `{ "url": <videoUrl>, "force_headful": <bool> }`.
- Parse success payload to capture `download_url`, `video_info`, `file_size`, `execution_time`.
- On non-200 status, map `error_code` to structured exceptions; bubble up to the strategy for retry decisions.

### Download Pipeline Changes
- `ScraplingApiDownloadStrategy` flow:
  1. Call download API (headless first) for each video and await them concurrently to match existing batch throughput expectations.
  2. Stream the returned `download_url` into the existing storage directory using `httpx` streaming to avoid loading whole file in memory.
  3. Persist metadata onto the `video` model (`duration_s`, `title`, `author`) and skip thumbnail storage (keyframes cover visual assets).
  4. Reuse existing `extract_keyframes` coroutine so keyframe extraction remains unchanged and persist keyframe metadata to the database when available (mirroring the `yt-dlp` path).
- Ensure file naming stays consistent (`{video_id}.mp4`) to avoid breaking cleanup jobs and test fixtures.
- Capture API telemetry in logs (include `execution_time`, `file_size`, strategy name such as `scrapling-api`).

### Error Handling
- Retry policy:
  - On `INVALID_URL` / input errors: fail fast without fallback (invalid request).
  - On `NAVIGATION_FAILED`, `NO_DOWNLOAD_LINK`, HTTP 5xx responses, or network errors (including timeouts): retry once immediately with `force_headful=true` (single retry only).
  - If retries are exhausted, emit structured errors and surface failure to callers; no automatic strategy switching.

### Configuration & Secrets
- Extend `config_loader.py` with:
  - `TIKTOK_DOWNLOAD_STRATEGY` (enum: `yt-dlp`, `scrapling-api`).
  - `TIKTOK_DOWNLOAD_TIMEOUT` (seconds) reuse for HTTP client, defaulting to `180` (3 minutes) if unspecified.
- Reuse existing headful retry defaults; no new toggle required.
- Document new env vars in `services/video-crawler/README.md`.
- Update `docker-compose` / env templates if available (validate with infra team).

### Observability
- Reuse `configure_logging` for the new strategy; emit logs like `download.strategy=scrapling-api`, `api.execution_time`, `api.error_code`.
- Add counters in `handlers/event_emitter.py` or new metrics module if available (count successes, retries, failures).
- Update alerts/dashboards if the team tracks download success rate.

## Implementation Plan
1. **Refactor existing downloader into strategies**
   - Move `download_video`, `extract_keyframes`, and `orchestrate_download_and_extract` logic into `YtDlpDownloadStrategy`.
   - Introduce abstract base / protocol and plug strategy selection in `TikTokDownloader.__init__`.
   - Ensure public methods (`download_videos_batch`, `orchestrate_download_and_extract`) remain backward compatible.
2. **Create API client and data models**
   - Implement `TikTokDownloadClient` with response/request dataclasses mirroring the guide (url, `force_headful` flag, `download_url`, `video_info`, `error_code`).
   - Centralize error mapping and retry decision hints in the client.
3. **Implement API-backed strategy**
   - Compose client + streaming downloader.
   - Execute `/tiktok/download` calls concurrently inside `download_videos_batch` (reuse semaphore pattern) to keep wall-clock time competitive.
   - Surface errors clearly after retries; no automatic handoff to `yt-dlp` once Scrapling succeeds (single source of truth).
   - Share keyframe extraction by delegating to existing extractor helper, including DB persistence for keyframes when the service has a DB connection.
4. **Wire configuration**
   - Ensure config exposes the new strategy option and thread values into `TikTokDownloader`.
   - Confirm existing headful-on-retry behaviour is honored without additional configuration.
   - Update service bootstrap (`tiktok_crawler.py`) to pass through config-driven overrides.
5. **Update logging & metrics**
   - Add structured logs for strategy selection, API timings, and retry usage.
   - Extend any existing metric emitters (if absent, plan to add simple counters/timers).
6. **Testing**
   - Unit tests for client (success, each error code, headful retry).
   - Unit tests for strategy selection (mock HTTP responses to validate failures bubble correctly without auto-switching).
   - Concurrency-focused tests (e.g., ensure multiple `/tiktok/download` calls are awaited together when batching).
   - Integration test exercising `VideoCrawlerService.process_video` with `TIKTOK_DOWNLOAD_STRATEGY=scrapling-api` (use `respx` or similar to stub HTTP).
   - Regression run of existing TikTok downloader tests to ensure no breakage.
7. **Documentation & rollout**
   - Update README + ops runbooks with new env vars and troubleshooting tips.
   - Provide runbook steps for switching strategies in production.

## Detailed To-Do List
1. **Configuration groundwork**
   - Update `services/video-crawler/config_loader.py` so `TIKTOK_DOWNLOAD_STRATEGY` accepts `scrapling-api` and remains defaulted to `yt-dlp`.
   - Mirror the new option in `.env.example`, deployment manifests, and README tables.
   - Sanity-check existing semaphore defaults for TikTok downloads (`NUM_PARALLEL_DOWNLOADS`).
2. **Restructure downloader module**
   - Create `platform_crawler/tiktok/download_strategies/` package; add `__init__.py` and a `protocol`/ABC (`TikTokDownloadStrategy`).
   - Move current synchronous `yt_dlp` implementation into `yt_dlp_strategy.py` (class `YtDlpDownloadStrategy`).
   - Extract shared helpers (storage path resolution, keyframe extraction, DB persistence) into reusable mixins or functions.
3. **Introduce Scrapling API client**
   - Add `platform_crawler/tiktok/tiktok_download_client.py` with async `resolve_download(url, force_headful)` and typed responses.
   - Implement structured exceptions for API error codes (`INVALID_URL`, `NAVIGATION_FAILED`, etc.).
   - Provide retry helper that toggles `force_headful` and surfaces execution metadata.
4. **Implement `ScraplingApiDownloadStrategy`**
   - Create `scrapling_api_strategy.py` that composes the client, streams the `download_url` to disk, and reuses shared keyframe extraction.
   - Enforce concurrent `/tiktok/download` calls using `asyncio.gather` + semaphore identical to existing batch logic (`NUM_PARALLEL_DOWNLOADS`).
   - Map API `video_info` onto crawler metadata (author, title, duration) and persist to the video record; skip thumbnail downloads.
   - Ensure keyframes are extracted and persisted to the database in the same way as the `yt-dlp` strategy.
   - Ensure error logging includes strategy name and API timing.
5. **Wire strategy factory**
   - Add factory in `download_strategies/factory.py` that reads config/env and returns the desired strategy.
   - Update `TikTokDownloader` to delegate `download_videos_batch` and `orchestrate_download_and_extract` through the selected strategy while keeping public method signatures unchanged.
6. **Concurrency and storage adjustments**
   - Confirm batch downloads await all Scrapling requests in parallel and respect per-platform download limits.
   - Reuse existing file naming (`{video_id}.mp4`) and ensure temporary files are cleaned up on failure.
7. **Logging & observability**
   - Emit structured logs like `download.strategy`, `scrapling_api.execution_time`, `scrapling_api.file_size`.
   - Add counters/timers if metrics plumbing exists; otherwise document required dashboards.
   - Extend troubleshooting runbook with Scrapling-specific failure modes.
8. **Testing**
   - Unit: mock HTTP client to cover success, all error codes, network failures, and headful retry.
   - Unit: verify strategy factory picks correct implementation for each env value and raises on invalid entries.
   - Unit: ensure parallel download orchestration schedules N tasks (use `asyncio` test helpers) and that keyframe persistence runs when DB fixtures are present.
   - Unit: confirm no follow-up `yt-dlp` execution occurs when Scrapling succeeds.
   - Integration: stub Scrapling endpoint via `respx`/`pytest-httpx` to validate end-to-end flow (download + keyframes).
   - Regression: run existing TikTok download tests to confirm `yt-dlp` path remains intact.
9. **Documentation & rollout**
   - Update `services/video-crawler/README.md`, sprint notes, and ops docs with Scrapling usage instructions.
   - Provide release notes and a toggle playbook for switching between strategies in staging/production.

## Testing Strategy
- **Unit**: Mock `httpx` responses covering success, known error codes, retries, and failure surfacing. Validate file persistence and metadata mapping.
- **Integration**: Spin up service in test harness with the Scrapling API strategy and confirm videos land in expected directories and keyframes create records.
- **Smoke in staging**: Enable `scrapling-api` in staging for a subset of jobs before full rollout.

## Rollout Plan
- Phase 1: Land code with strategy defaulting to `yt-dlp`; deploy and confirm no regressions.
- Phase 2: Enable `scrapling-api` in staging, monitor success rate and error logs.
- Phase 3: Flip production env var to `scrapling-api` for limited workloads, monitor metrics, then expand if stable.
- Maintain ability to revert by toggling env var without redeploying.

## Risks & Mitigations
- **API instability**: Provide clear logging and alerting so operators can switch back to `yt-dlp` manually if required.
- **HTTP client resource leaks**: Reuse a shared async client, close it gracefully (mirror `TikTokSearcher` lifecycle).
- **Large file downloads**: Stream to disk, enforce size caps similar to existing logic.
- **Test brittleness**: Provide helpers for strategy injection to simplify mocking.

## Open Questions
- Do we need to persist `video_info` metadata (author, duration) into the database now or later?
- Should force-headful retries be configurable per-job or globally?
- Are there rate limits for the new endpoint that require client-side throttling beyond current semaphore?
