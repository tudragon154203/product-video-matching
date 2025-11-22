# Sprint 15 — Evidence Builder Backend + Front‑End Plan (repo‑synced)

> Scope: Evidence generation service (`services/evidence-builder`) plus UI surfaces in `services/front-end` that expose evidence.  
> Status: Draft after codebase deep-dive (Oct 2025).  
> Owner: PVM team

---

## 1) Purpose
- Stabilize the evidence-builder so it reliably consumes `match.result`/`match.results.completed`, renders deterministic artifacts, and only emits `evidences.generation.completed` when all matches are covered (including zero-match jobs).
- Ship a first-class evidence experience in the front-end (job detail + match detail) that shows thumbnails, full-resolution artifacts, and status when evidence is pending or failed.

---

## 2) Current State (repo scan)

### Backend (Python service)
- Entry: `services/evidence-builder/main.py` subscribes to `match.result` and `match.results.completed` and loops forever. Prefetch is set (10 for per-asset, 1 for completion).
- Handlers: `handlers/evidence_handler.py` wraps `EvidenceBuilderService` but **does not accept `correlation_id`**, even though `common_py.messaging_handler` invokes handlers as `(event_data, correlation_id)`. This currently raises `TypeError` on real messages. No schema validation decorator is applied.
- Service flow (`services/service.py`):
  - Validates required fields manually; pulls `img_id`/`frame_id` from `best_pair`.
  - Fetches asset paths and kp blobs from Postgres (`MatchRecordManager` uses raw queries on `product_images`/`video_frames`).
  - Calls `EvidenceGenerator.create_evidence(...)` to build a side-by-side JPG under `<DATA_ROOT>/evidence/`. Keypoint overlays are **randomly synthesized**, not derived from stored `kp_blob_path`.
  - Updates `matches.evidence_path` and immediately asks `EvidencePublisher` to publish `evidences.generation.completed`.
  - Zero-match path: `handle_match_results_completed` delegates to publisher, which publishes completion when count == 0.
- Publisher (`services/evidence-builder/services/evidence_publisher.py`):
  - Holds an in-memory `processed_jobs` set only; restarts will re-publish completions.
  - Emits `evidences.generation.completed` **as soon as the first evidence is written**. It never waits for all `matches` rows to have `evidence_path`, so jobs can be marked complete prematurely.
  - Does not record phase events or idempotency in DB; no retry/backoff at service level (relies on broker DLQ only).
- Generation (`evidence.py` + `evidence_image_renderer.py`):
  - Uses OpenCV to resize and compose two panels. Text overlays include score/timestamp/ids. No watermarking or metadata persistence.
  - When kp paths exist, overlays draw 5 random lines (placeholders). Does not read actual kp data.
- Config: `config_loader.py` pulls `DATA_ROOT_CONTAINER` for output dir; service uses `/app/app` working dir via Compose. No tunable batch/concurrency limits besides RabbitMQ prefetch.
- Missing pieces:
  - No contract validation (`contracts/validator`) on ingress.
  - No idempotency by `event_id` or `correlation_id` for `match.result`.
  - No health/readiness endpoint; no metrics.
  - No URL building; only raw `evidence_path` written to DB.
  - Dockerfile only installs deps/libs; relies on bind mount for code (ok for dev, not production).

### Front-End (Next.js `services/front-end`)
- Job detail (`app/[locale]/jobs/[jobId]/page.tsx`) renders the **MatchingPanel** during `matching|evidence|completed`.
- Matching UI (`components/jobs/MatchingPanel/*.tsx`):
  - `MatchingSummaryCards` shows `matches_with_evidence` count, but only as a progress bar.
  - `MatchingResultsTable` lists matches with a ready/pending badge derived from `match.evidence_path`; there is **no evidence thumbnail or viewer**.
  - Polling uses `useJobMatches` with min_score slider; cannot filter by evidence-ready.
- API client (`lib/api/services/result.api.ts`) exposes `getEvidence`, but it is **unused**. Zod schema `EvidenceResponse` only returns `evidence_path`; `evidence_url` is missing even though backend models include it.
- Data contract gaps:
  - `MatchResponse` omits `evidence_url` (present in `services/main-api/models/results_schemas.py`).
  - Main API `results_endpoints.get_evidence` returns only `evidence_path`; `StaticFileService.build_full_url` currently builds local paths (not HTTP URLs).
- UX gaps:
  - No per-match drawer/lightbox to show the artifact.
  - No link to jump to video timestamp, download, or view metadata.
  - No surfaced failures or “still rendering” states beyond the badge.

---

## 3) Goals & Non-Goals
- Goals:
  1. Contract-correct ingestion with retries and idempotency that survives restarts.
  2. Generate deterministic, inspectable evidence artifacts and store them predictably under `/app/data/evidence/{job_id}/`.
  3. Emit `evidences.generation.completed` only when **all** matches for the job have an evidence asset, or immediately when `match.results.completed` sees zero matches.
  4. Expose `evidence_url` via main-api so UI can fetch images through `/files/...`.
  5. Front-end: show evidence thumbnails in the matching table, full-size viewer with product/video context, and clear pending/failed states.
- Non-Goals (this sprint):
  - Generating video clips; we stay on image composites.
  - Redesigning matching heuristics or contracts for `match.result`.

---

## 4) Backend Plan (evidence-builder + main-api touchpoints)

### 4.1 Contracts, handlers, idempotency
- Align handler signatures with broker (`async def handle_match_result(event_data, correlation_id)`), and attach `@validate_event("match_result")` / `@validate_event("match_results_completed")` in `handlers/evidence_handler.py`.
- Use `correlation_id` or a derived deterministic key (`job_id` + `product_id` + `video_id` + `best_pair.img_id` + `best_pair.frame_id`) to dedupe per-match generation and to guard against retries/DLQ replays.
- Write a lightweight `processed_events` table or reuse `phase_events` to persist `match.result` processing (mirroring matcher idempotency), so restarts don’t regenerate the same evidence twice.

### 4.2 Evidence generation flow
- Directory layout: `/app/data/evidence/{job_id}/{match_id}.jpg` (or `{img_id}_{frame_id}.jpg` if `match_id` unavailable). Ensure `evidence_dir.mkdir(..., exist_ok=True)` per job to avoid collisions.
- Replace placeholder kp overlay with real data:
  - Load AKAZE/SIFT kp/descriptors from `kp_blob_path` if present (compressed npy? verify upstream format).
  - Draw true inlier lines (fallback to simple side-by-side if blobs unreadable).
- Embed metadata (JSON sidecar or EXIF) with `score`, `ts`, `product_id`, `video_id`, `img_id`, `frame_id`, and match timestamp for traceability.
- Add deterministic coloring and watermark (service name + job_id) to prevent tampering.

### 4.3 Completion semantics
- Track match totals per job (`SELECT COUNT(*) FROM matches WHERE job_id = $1`) and evidence-written count (`evidence_path IS NOT NULL`).
- On `match.result`:
  - Generate evidence → update `matches.evidence_path`.
  - Re-count evidence-ready matches; if `evidence_ready == total_matches`, emit `evidences.generation.completed`.
- On `match.results.completed`:
  - If `total_matches == 0`, emit completion immediately.
  - Else, log and wait for per-match completions (no-op).
- Persist completion emission (e.g., into `phase_events` or `processed_jobs` table) so we never double-send across restarts.

### 4.4 Observability & resilience
- Add structured logging around asset loads, generation duration, output size, and retry attempts.
- Expose `/health` returning DB/Broker connectivity and writable evidence dir.
- Metrics: counters for evidence generated, failures, completion latency per job; gauge for backlog (matches without evidence).
- Backpressure: respect broker prefetch; consider semaphore to cap concurrent OpenCV work.

### 4.5 Serving + API integration (main-api)
- Update `services/main-api/services/results/results_service.py` to populate `evidence_url` using `StaticFileService.build_url_from_local_path(evidence_path)`.
- Fix `StaticFileService.build_full_url` to use API base (`{PUBLIC_IMAGE_BASE_URL or http://<host>:<port>/files/...}`) instead of filesystem paths.
- Extend `EvidenceResponse` to include `evidence_url`; dust off contract tests (`tests/contract/http/test_api_contract_updates.py`) to assert URLs.
- Ensure `results_endpoints.get_evidence` validates existence and returns both path/url; return 202/404 appropriately if evidence pending/missing.

---

## 5) Front-End Plan

### 5.1 Data contracts & hooks
- Extend Zod schemas (`lib/zod/result.ts`) to include `evidence_url` (nullable) for list/detail/evidence responses.
- Wire `resultsApiService.getMatch` and `getEvidence` to return `evidence_url`; handle `null` gracefully.
- Add `useEvidence(matchId)` hook with polling/backoff while `evidence_url` is null but job is in `evidence` phase.

### 5.2 UI/UX changes (job detail)
- Matching table:
  - Add evidence thumbnail column (fit 64x64) using `evidence_url`; show skeleton/pending badge when absent.
  - Filter toggle “Evidence ready only”.
  - Clicking a row opens a right-side drawer/lightbox showing full evidence image, product details, video title/platform, score, timestamp, and download link.
- Summary cards:
  - Surface evidence completion percent with status text (“6 of 10 matches have evidence; building…”).
  - Show “evidence lagging” indicator if `phase === 'completed'` but `matches_with_evidence < matches_found`.
- Error states: render a retry CTA if `getEvidence` 404s while `phase === evidence` (graceful; don’t crash table).

### 5.3 Navigation & sharing
- Provide copyable `/files/...` link and `Download evidence` CTA in the drawer.
- Add “Open video at t=ts” link (best-effort: use `video.url` + `?t=ts` for YouTube).

### 5.4 Testing
- Unit: Zod schema updates, hooks (polling logic), thumbnail rendering states.
- Component: Matching table shows thumbnail/pending/failed; drawer renders metadata.
- E2E (Playwright): Start job → wait through matching/evidence → evidence thumbnail appears → drawer loads image URL (mocked).

### 5.5 Performance & accessibility
- Lazy-load thumbnails, use `next/image` with blur placeholder.
- Keyboard navigation for drawer/lightbox; alt text includes product + video title.

---

## 6) Risks & Open Questions
- `kp_blob_path` format is not documented in repo—confirm how vision-keypoint writes kp blobs before implementing true overlays.
- `match.result` lacks `event_id`; dedup will rely on correlation_id or derived keys—consider extending contract for stronger idempotency.
- main-api currently subscribes only to collection/feature events; matcher manually sets job phase to `evidence`. We must ensure `evidences.generation.completed` is recorded/persisted so job completion is robust even without a subscriber.
- Public URL base: need a single source of truth (`PUBLIC_IMAGE_BASE_URL` or derive from request host) to avoid hardcoding container paths.

---

## 7) Deliverables & Timeline (proposed)
1. **Backend hardening (2–3 days):** handler signature/validation fix, deterministic file layout, completion counter, persistence of completion, main-api evidence_url plumbing.
2. **Rendering upgrade (1–2 days):** real kp overlay (or deterministic noop fallback), metadata sidecar, watermark.
3. **Frontend evidence UX (3–4 days):** schema/hook updates, thumbnail column + filter, drawer/lightbox, tests.
4. **Observability (1 day):** health endpoint, logging, counters, dashboards follow-up.

If time-limited, prioritize 1 → 3 to unblock operators, then 2 for quality of artifacts.

---

## 8) Execution TODOs (Backend first, Front-end later)

### Backend (must complete before FE)
- [ ] Fix handler signature mismatch: accept `correlation_id` and validate events with `@validate_event("match_result")` / `@validate_event("match_results_completed")`.
- [ ] Implement idempotency/dedup per match (`event_id` or deterministic composite key) and persist processed events (DB-backed, not in-memory).
- [ ] Correct completion semantics: emit `evidences.generation.completed` only when all `matches` rows for the job have evidence or when total matches == 0.
- [ ] Make evidence outputs deterministic: stable file naming under `/app/data/evidence/{job_id}/`, no random kp overlays; embed metadata and watermark; handle kp blobs if present.
- [ ] Harden asset loading and error handling (retries/backoff, structured logs, DLQ-friendly failures).
- [ ] Expose evidence URL via main-api (`StaticFileService.build_full_url` using public base, `EvidenceResponse` includes `evidence_url`) and ensure path validation.
- [ ] Add health/readiness for evidence-builder (DB, broker, writable evidence dir) plus counters/metrics for evidence backlog and failures.

### Front-end (after backend is stable)
- [ ] Extend Zod schemas and API client to surface `evidence_url`; update matching hooks to poll while evidence pending.
- [ ] Add evidence thumbnail column + “Evidence ready” filter; render drawer/lightbox with full image, metadata, download/share link, and “open video at t=ts”.
- [ ] Handle pending/failed evidence states gracefully with retry CTA; add unit/component/Playwright coverage for evidence flows.
