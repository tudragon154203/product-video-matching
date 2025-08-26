# Parallel Video‑Crawler — Cross‑Platform Spec

## 1) Scope & Goals
- For each job, run **each platform crawler concurrently** (e.g., YouTube, TikTok, Instagram Reels, etc.).
- Within each platform, allow **multiple downloads in parallel**, bounded by a per‑platform semaphore.
- Preserve per‑platform grouping, deduplicate by `video_id`, and tolerate partial failures.
- Emit structured logs that let us **prove** parallel execution (overlapping timestamps, semaphore limits, inflight counters).

> This spec assumes an existing service layer (e.g., `VideoCrawlerService`), a generic `VideoFetcher` abstraction per platform, and a shared logging utility.

---

## 2) Configuration
Add/confirm these env keys (e.g., `services/video-crawler/.env`):

- `VIDEO_DIR` — root path for downloaded assets.
- `NUM_VIDEOS` — target videos per **(platform, query)**.
- `NUM_PARALLEL_DOWNLOADS` — **per‑platform** max concurrent downloads.
- `LOG_LEVEL` — logger level (`DEBUG|INFO|WARN|ERROR`).
- **New (optional):** `MAX_CONCURRENT_PLATFORMS` — global cap for simultaneous platforms (default: `len(platforms)` for the job).

> Load these via your existing config loader. `NUM_PARALLEL_DOWNLOADS` should be enforced inside each platform crawler; `MAX_CONCURRENT_PLATFORMS` is enforced at the orchestration layer.

---

## 3) Contracts & Inputs
**Ingested message/event** (example): `videos.search.request`
```json
{
  "job_id": "string",
  "platforms": ["youtube", "tiktok"],
  "queries": ["string"],
  "recency_days": 30,
  "num_videos": 10
}
```
- The service maps each `platform` to its supported `queries` set, then calls the corresponding crawler via a generic entrypoint, e.g. `VideoFetcher.search_platform_videos(...)`.
- The entrypoint returns a list of normalized video records; each record must include at least: `{ platform, video_id, title, url, duration_s, published_at, filepaths, ... }`.

---

## 4) Orchestration Model
**Service layer** (e.g., `VideoCrawlerService.handle_videos_search_request`):
1. Parse `job_id`, `platforms`, `queries`, `recency_days`, `num_videos`.
2. Build `platform_queries` map (may be the same `queries` for all platforms or platform‑specific subsets).
3. Create a **platform‑level semaphore** sized by `MAX_CONCURRENT_PLATFORMS` (or `len(platforms)` if unset).
4. Launch one async task per platform using `asyncio.gather(*tasks, return_exceptions=true)`.
5. Merge all successful results; store/emit job progress; continue the pipeline (e.g., keyframes, feature extraction) as needed.

**Within each platform crawler**:
- Use a **download‑level semaphore** sized by `NUM_PARALLEL_DOWNLOADS`.
- Deduplicate by `video_id` before enqueuing downloads.
- Respect `NUM_VIDEOS` as a hard cap per **(platform, query)**.
- Apply crawler‑specific retries/backoff; on failure, log and skip the item (do not crash the job).

---

## 5) Deduplication & Limits
- **Per‑platform dedupe** by `video_id` (normalize ID format first).
- Enforce `NUM_VIDEOS` at the crawler boundary to avoid over‑fetching.
- Optionally, score/sort candidates (e.g., by recency, view count) before applying the cap.

---

## 6) Error Handling & Backoff
- Cross‑platform orchestrator must **not** fail‑fast. Use `return_exceptions=true` in `gather`, inspect results, and continue with available platforms.
- Per‑platform crawler catches transient exceptions and retries with exponential backoff (jitter). On terminal errors, return `[]` and emit an error log including `platform` and `error_type`.
- The service should emit a summary at the end: platforms attempted, successes, failures, total videos collected.

---

## 7) Logging — Verifiable Concurrency
Use structured logging (JSON) throughout. Required fields:
- **Common**: `job_id`, `platform`, `stage`, `started_at`, `ended_at`, `elapsed_ms`.
- **Platform‑task stages**: `platform.start`, `platform.done`, with `query_count`, `video_count`.
- **Download stages**: `download.start`, `download.done`, with `video_id`, `semaphore_limit` (= `NUM_PARALLEL_DOWNLOADS`), and `inflight_downloads` (optional counter) to demonstrate parallelism.

**Example flow:**
- `INFO platform.start` → `INFO platform.done` entries for each platform with overlapping time windows.
- `DEBUG download.start` / `DEBUG download.done` repeated rapidly with inflight > 1 up to the configured limit.

---

## 8) Metrics (Optional but Recommended)
If a metrics exporter exists, add:
- **Counters**: `crawler_platform_started_total{platform}`, `crawler_platform_completed_total{platform}`, `crawler_download_started_total{platform}`, `crawler_download_completed_total{platform}`.
- **Histograms**: `crawler_platform_duration_ms{platform}`, `crawler_download_duration_ms{platform}`.

---

## 9) Pseudocode (Service Layer)
```python
# inside VideoCrawlerService.handle_videos_search_request(...)
logger.info("Processing video search request", extra={
    "job_id": job_id,
    "platforms": platforms,
    "queries": queries,
})

plat_sem = asyncio.Semaphore(MAX_CONCURRENT_PLATFORMS or len(platforms))

async def run_platform(platform: str, pqueries: list[str]):
    async with plat_sem:
        t0 = time.perf_counter_ns()
        logger.info("platform.start", extra={
            "job_id": job_id,
            "platform": platform,
            "query_count": len(pqueries),
        })
        try:
            videos = await video_fetcher.search_platform_videos(
                platform=platform,
                queries=pqueries,
                recency_days=recency_days,
                download_dir=VIDEO_DIR,
                num_videos=NUM_VIDEOS,
            )
        except Exception as e:
            logger.error("platform.error", extra={
                "job_id": job_id,
                "platform": platform,
                "error": repr(e),
            })
            videos = []
        elapsed_ms = (time.perf_counter_ns() - t0) // 1_000_000
        logger.info("platform.done", extra={
            "job_id": job_id,
            "platform": platform,
            "video_count": len(videos),
            "elapsed_ms": elapsed_ms,
        })
        return videos

results = await asyncio.gather(
    *[run_platform(p, platform_queries[p]) for p in platforms],
    return_exceptions=True,
)

videos = []
for r in results:
    if isinstance(r, Exception):
        # already logged in run_platform; skip
        continue
    videos.extend(r)

if not videos:
    logger.info("no_videos", extra={"job_id": job_id})
    return {"job_id": job_id, "videos": []}

# downstream pipeline continues here (e.g., keyframes, features)
return {"job_id": job_id, "videos": videos}
```

---

## 10) Acceptance Criteria
1. **Cross‑platform parallelism**: With `platforms = ["youtube", "tiktok"]`, logs show overlapping `platform.start` → `platform.done` windows.
2. **Per‑platform parallelism**: Logs show `download.start`/`download.done` with `inflight_downloads` > 1 up to `NUM_PARALLEL_DOWNLOADS`.
3. **Resilience**: If one platform fails, others still complete; summary log lists the failure and the job returns available results.
4. **Zero‑result path**: When all platforms return empty, the service returns `{videos: []}` and logs `no_videos` without crashing.
5. **No contract changes**: Continues to consume the existing `videos.search.request` shape; new env key `MAX_CONCURRENT_PLATFORMS` is optional.

---

## 11) Implementation Notes
- Ensure each platform module **normalizes `video_id`** early (e.g., strip URL params, decode short links).
- Use an **async‑safe bounded executor** for any CPU‑bound steps (e.g., heavy thumbnail decoding) to avoid blocking the event loop.
- Keep platform‑specific scraping/API logic encapsulated; the orchestrator must remain platform‑agnostic.
- Prefer **idempotent downloads** (check file existence by deterministic path) to survive restarts.
- Emit **progress events** (if applicable) so the UI can reflect per‑platform progress in real time.

