# Sprint 5 — Retire TikTokApi From Video Crawler (Specs & Plan)

## Context & Problem Statement
The current TikTok integration in `video-crawler` relies on the Python package `TikTokApi` (v6.2.2), which does not reliably support keyword search for videos and is operationally brittle (session creation, headless browser requirements, geo/IP sensitivity). Continuing to depend on it blocks consistent keyword-driven discovery and increases maintenance burden.

Goal of this sprint: fully retire the TikTokApi-based path from `video-crawler`, deprecate TikTok keyword search, and make a clean breaking change that removes TikTok support without backward compatibility shims.

Non-goal: building an alternative TikTok keyword search solution in this sprint (e.g., SERP-based discovery, web scraping, or third-party APIs). That can be scoped as a future spike/implementation.


## Scope
- Remove TikTokApi usage and delete its dependent modules in `video-crawler`.
- Remove TikTok as a supported platform for keyword search (breaking change).
- Enforce request rejection when `tiktok` is requested (422 from orchestrator), rather than tolerating/ignoring it.
- Update docs, contracts, tests, and seeds to reflect removal.

Out of scope:
- Implementing a new TikTok search mechanism.


## Impacted Areas (references)
- TikTok API client and crawler stack:
  - `services/video-crawler/platform_crawler/tiktok/tiktok_api_client.py`
  - `services/video-crawler/platform_crawler/tiktok/tiktok_searcher.py`
  - `services/video-crawler/platform_crawler/tiktok/tiktok_downloader.py`
  - `services/video-crawler/platform_crawler/tiktok/tiktok_crawler.py`
- Crawler wiring and platform map:
  - `services/video-crawler/services/service.py:14`
  - `services/video-crawler/services/service.py:56`
  - `services/video-crawler/services/service.py:100`
  - `services/video-crawler/services/service.py:194`
- Service config and env:
  - `services/video-crawler/config_loader.py`
  - `services/video-crawler/.env.example`
  - `services/video-crawler/requirements.txt`
- Tests and sample data referencing TikTok:
  - `services/video-crawler/tests/tiktok/test_crawler.py`
  - `scripts/seed.py`
- Downstream/adjacent mentions (docs and API):
  - `API.md:181` (platform filter examples include tiktok)
  - `services/main-api/api/video_endpoints.py:67` (docstring mentions tiktok)


## Design Decisions
- Remove `TikTokApi` from runtime dependencies and delete TikTok crawler components.
- Keep the platform interface pluggable; do not introduce any TikTok-specific feature flags or env vars.
- Hard-fail at validation time in `main-api` when `tiktok` is included (HTTP 422). Do not silently ignore.
- `video-crawler` contains no TikTok code paths or fallbacks after this sprint.


## Behavioral Spec
- `main-api` rejects any job request containing `tiktok` in `platforms` with 422 and error message: "TikTok keyword search is retired and unsupported."
- `video-crawler` does not list or initialize a TikTok crawler; no attempt to search or download TikTok videos.
- Service builds and runs without `TikTokApi` and without browser/session overhead.


## API/Contracts
- Mark TikTok keyword search as “retired/unsupported”.
- Validate in `main-api` to reject `tiktok` with 422 and a clear message.
- Remove TikTok from public examples and platform enums where applicable (front-end zod schemas, docs).


## Tasks & Checklist
1) Dependency and module cleanup
- [ ] Remove `TikTokApi` and related dependencies from `services/video-crawler/requirements.txt` (e.g., `TikTokApi`, possibly `playwright` if unused elsewhere).
- [ ] Delete the TikTok crawler stack under `services/video-crawler/platform_crawler/tiktok/` (no gating or flags).
- [ ] Remove imports/usages in `services/video-crawler/services/service.py` and platform registry wiring.

2) Configuration cleanup
- [ ] Remove TikTok-specific env vars from `services/video-crawler/.env.example` and `config_loader.py`.
  (No new env vars introduced.)

3) Request validation
- [ ] Update `main-api` validation to reject `tiktok` in `platforms` with 422 and message.

4) Tests & seeds
- [ ] Remove/adjust `services/video-crawler/tests/tiktok/test_crawler.py` and any tests pinning TikTok.
- [ ] Update seeds that randomly assign `platform: "tiktok"` (see `scripts/seed.py`) to avoid generating TikTok items, or make them deterministic to supported platforms.
- [ ] Run integration tests with infra up to validate non-regression on YouTube-only flows.
 - [ ] Front-end tests: remove/adjust cases that expect TikTok labels/images.

5) Docs & UI updates
- [ ] Update `API.md` to remove TikTok from examples and note retirement.
- [ ] Update sprint docs (this file) and optionally `README.md` to reflect removal.
- [ ] Update front-end platform enums/labels to remove TikTok (e.g., `services/front-end/lib/zod/job.ts`, `components/advanced-options.tsx`, tests).
- [ ] Note migration in `CONTRACTS.md` if any contract-level behavior shifts (e.g., platform handling notes).

6) Observability & Ops
- [ ] Verify no remaining dashboards/alerts depend on TikTok crawler metrics.


## Acceptance Criteria
- Service builds and runs without `TikTokApi`; no TikTok imports remain in `services/video-crawler`.
- `main-api` rejects any request containing `tiktok` with 422 and informative error.
- Front-end does not offer TikTok as a selectable platform; tests updated accordingly.
- Docs updated to reflect retirement; integration tests pass for supported platforms.


## Migration Plan
- Single cutover:
  1) Remove deps and delete TikTok modules; wire out from platform registry.
  2) Update `main-api` validation to 422 on TikTok; update UI/platform schemas; adjust tests and seeds.
  3) Update docs across repo; run integration tests.

Rollback:
- Re-add `TikTokApi` in `requirements.txt`, restore module imports, and revert docs. Low-risk if changes are isolated.


## Risks & Mitigations
- Risk: Hidden references break runtime after library removal.
  - Mitigation: Search-and-destroy pass plus CI check that fails on TikTok symbols.
- Risk: Stakeholders expect TikTok results.
  - Mitigation: Communicate deprecation; schedule a spike for alternative discovery.


## Future Work (separate spike)
- Evaluate alternatives for TikTok keyword discovery:
  - SERP-based discovery (e.g., search engine APIs) extracting TikTok links.
  - Headless browser approach with robust ToS/legal review and rate limiting.
  - Third-party APIs with contractual support for keyword search.
- Prototype minimal viable path and compare reliability, latency, and compliance.
