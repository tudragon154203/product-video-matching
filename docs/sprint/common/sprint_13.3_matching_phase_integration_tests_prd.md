# Sprint 13.3 — Matching Phase Integration Tests PRD (Happy Path + Critical)

Status: 🟡 Planned – Matching-phase coverage targeted for Sprint 13.3  
Owners: QA/Infra  
Related docs: [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml), [RUN.md](../../RUN.md), [infra README](../../infra/pvm/README.md), [sprint_12_unified_test_structure.md](./sprint_12_unified_test_structure.md), [sprint_13.2_feature_extraction_phase_integration_tests_prd.md](./sprint_13.2_feature_extraction_phase_integration_tests_prd.md), [sprint_2_matcher_microservice_implementation.md](../matcher/sprint_2_matcher_microservice_implementation.md), [test_feature_extraction_to_matching_transition.py](../../tests/integration/test_feature_extraction_to_matching_transition.py:28)

## 1) Overview and Objectives
- Purpose: 🟡 Deliver an end-to-end matching phase integration suite that exercises `match.request` ingestion through `matchings.process.completed`, validating persistence and emissions across the live stack.
- Objectives:
  - 🟡 Contract fidelity for ingress/egress events (`match.request`, `match.result`, `matchings.process.completed`) and supporting DB writes.
  - 🟡 Validate job transitions to `evidence` driven by [PhaseTransitionManager._process_matching_phase](../../services/main-api/services/phase/phase_transition_manager.py:115).
  - 🟡 Prove matcher idempotency by replaying identical events and asserting [EventCRUD.record_event](../../libs/common-py/common_py/crud/event_crud.py:8) suppresses duplicates.
- Non-goals:
  - ❌ DLQ stress tests or long-run retry backoff scenarios.
  - ❌ Load/performance benchmarking of vector search or scoring components.
  - ❌ Evidence builder rendering validations (covered in downstream evidence-phase suite).

## Implementation Status
- ✅ Transition coverage exists: [test_feature_extraction_to_matching_transition.py](../../tests/integration/test_feature_extraction_to_matching_transition.py:28) validates feature extraction completion triggers `match.request` and phase promotion to `matching`.
- 🟡 No integration test currently drives [MatcherService.handle_match_request](../../services/matcher/services/service.py:43) against live Postgres/RabbitMQ.
- 🟡 Test data lacks deterministic embeddings/keypoints required by [MatchingEngine.match_product_video](../../services/matcher/matching/__init__.py:50) to emit consistent matches.
- 🟡 No assertions exist for [MatchCRUD.create_match](../../libs/common-py/common_py/crud/match_crud.py:9), [processed_events](../../infra/migrations/versions/005_add_processed_events_table.py:18), or `match.result` routing.

## 2) Actors and Systems
- 🟡 `matcher` service: entry point [MatcherHandler.handle_match_request](../../services/matcher/handlers/matcher_handler.py:24) delegates to [MatcherService.handle_match_request](../../services/matcher/services/service.py:43) which persists matches and publishes completion.
- 🟡 `main-api`: phase orchestration via [PhaseTransitionManager.check_phase_transitions](../../services/main-api/services/phase/phase_transition_manager.py:15) and `_process_matching_phase` to promote jobs on `matchings.process.completed`.
- 🟡 RabbitMQ `product_video_matching` topic exchange observed through [MessageSpy](../../tests/support/spy/message_spy.py:61) for `match.request`, `match.result`, and completion events.
- 🟡 Postgres surfaces: `products`, `product_images`, `videos`, `video_frames`, `matches`, `processed_events`, and `phase_events` defined in [001_initial_schema](../../infra/migrations/versions/001_initial_schema.py:108) and [005_processed_events](../../infra/migrations/versions/005_add_processed_events_table.py:18).
- 🟡 Observability: out of scope for this sprint; rely on existing logging without additional validation.

## 3) Event Contracts and Data Surfaces
- Input contract: [match_request.json](../../libs/contracts/contracts/schemas/match_request.json) published by `main-api`.
- Output contracts:
  - [match_result.json](../../libs/contracts/contracts/schemas/match_result.json) emitted per accepted product/video pair.
  - [matchings_process_completed.json](../../libs/contracts/contracts/schemas/matchings_process_completed.json) emitted once per job.
- Persistence and ledgers:
  - `matches` via [MatchCRUD.create_match](../../libs/common-py/common_py/crud/match_crud.py:9).
  - Idempotency ledger `processed_events` via [EventCRUD](../../libs/common-py/common_py/crud/event_crud.py:8) to block duplicate processing.
  - Phase tracking `phase_events` in [001_initial_schema](../../infra/migrations/versions/001_initial_schema.py:139) ensuring `main-api` barrier logic remains aligned.
- Data access expectations: [MatchingEngine.get_product_images](../../services/matcher/matching/__init__.py:137) and [get_video_frames](../../services/matcher/matching/__init__.py:150) require populated embeddings and keypoint blob paths for deterministic scoring.

## 4) Environment, Configuration, Preconditions
- Compose the full stack with `docker compose -f infra/pvm/docker-compose.dev.yml up -d` (services must include `main-api`, `matcher`, Postgres, RabbitMQ).
- Apply migrations prior to tests via `python scripts/run_migrations.py upgrade`; ensure `processed_events` table exists (revision 005).
- Use `.env.test` defaults plus `INTEGRATION_TESTS_ENFORCE_REAL_SERVICES=true` so fixtures enforce real service usage (`tests/conftest.py:84`).
- Reuse shared fixtures: `db_manager` ([tests/conftest.py:136](../../tests/conftest.py:136)), `message_broker` ([tests/conftest.py:146](../../tests/conftest.py:146)), `clean_database` ([tests/conftest.py:163](../../tests/conftest.py:163)) for isolation.
- Ensure `data/tests/**` assets are mounted inside containers so embeddings/keypoints referenced by tests are reachable from `/app/data/tests/...`.

## 5) Test Data and Fixtures
- Extend [tests/mock_data/test_data.py](../../tests/mock_data/test_data.py:16) with helpers that attach deterministic `emb_rgb`, `emb_gray`, and `kp_blob_path` values to products and frames (store fixtures under `data/tests/features/` or reuse `data/keypoints/*.npz`).
- Provide combined dataset builders that return product/video records plus ready-to-publish events, mirroring `build_product_dataset` in transition tests while including embeddings for scoring.
- Introduce a `matching_test_environment` fixture (new module under `tests/support/fixtures/`) composing:
  - `MessageSpy` queues for `match.result` and `matchings.process.completed`.
  - Database cleanup leveraging [CollectionPhaseCleanup](../../tests/support/validators/db_cleanup.py:27) but scoped to job ids injected by matching tests.
  - Extended `DatabaseStateValidator` assertions for matches, processed events, and job phases.
  - Event publisher capable of emitting `match.request` (add `publish_match_request` helper to [event_publisher.py](../../tests/support/publisher/event_publisher.py:430)).
- Augment `expected_observability_services` ([tests/conftest.py:112](../../tests/conftest.py:112)) with matching-phase checkpoints so the validator asserts `matcher` logs appear when tests run.

## 6) Proposed Test Suite

### 6.1) Matching — Full Pipeline With Acceptable Pair
- **Setup**: Seed a job in Postgres with products/images and video/frames using new builders (embeddings + keypoints), set job phase to `matching`, and record prerequisite phase events so `main-api` considers feature extraction complete.
- **Execution**: Publish a schema-valid `match.request` with deterministic `event_id`; wait for `match.result` via spy and completion event.
- **Validations**:
  - Assert `match.result` payload matches [match_result.json](../../libs/contracts/contracts/schemas/match_result.json), including `best_pair.score_pair` ≥ `MATCH_BEST_MIN` (config in [services/matcher/config_loader.py:8](../../services/matcher/config_loader.py)).
  - Confirm `matches` table contains persisted rows for each accepted pair with scores mirrored from payload.
- Ensure `matchings.process.completed` event fired exactly once and job phase advanced to `evidence` (verify via [DatabaseStateValidator.assert_job_phase](../../tests/support/validators/db_cleanup.py:347)).
  - Check `processed_events` contains the dispatched `event_id`.
- **Notes**: No new events or schema changes required; reuse existing routing keys and tables.

### 6.2) Matching — Zero Acceptable Matches (Fail-Gating)
- **Setup**: Seed datasets where embeddings fall below `SIM_DEEP_MIN` or acceptance thresholds (e.g., deliberately offset vectors).
- **Execution**: Publish `match.request`; await `matchings.process.completed` without expecting `match.result`.
- **Validations**:
  - Assert no `match.result` events were captured and `matches` table has zero inserts.
  - Verify completion event still stored in `phase_events` and job transitions to `evidence` (ensuring zero-match path aligns with [MatchAggregator._apply_acceptance_rules](../../services/matcher/matching_components/match_aggregator.py:79)).
- **Notes**: Verify that no `match.result` is emitted and no additional DB structures are needed.

### 6.3) Matching — Idempotent Re-delivery
- **Setup**: Reuse happy-path data; ensure `processed_events` empty before start.
- **Execution**: Publish the same `match.request` twice (identical `event_id`). Optionally publish a second event with new `event_id` to prove new work still runs.
- **Validations**:
  - Assert `match.result` events and DB inserts occur only once per `event_id`.
  - Confirm `processed_events` retains the first `event_id` and that second identical dispatch is logged as skipped (`Match request already processed` from [MatcherService.handle_match_request](../../services/matcher/services/service.py:50)).
  - Ensure no duplicate completion events.

### 6.4) Matching — Partial Asset Availability (Fallback Coverage)
- **Setup**: Seed products with embeddings but missing keypoints, and frames with minimal embeddings to trigger [PairScoreCalculator.calculate_keypoint_similarity](../../services/matcher/matching_components/pair_score_calculator.py:70) fallback behaviour.
- **Execution**: Publish `match.request`; rely on fallback scoring to produce sub-threshold matches.
- **Validations**:
  - Verify fallback path logs "Missing keypoint blob path" and resulting scores respect weighted combination (embedding dominates).
  - Assert accepted matches only occur when embedding-only score crosses thresholds; otherwise ensure zero-match handling consistent.
- **Notes**: Confirm fallback paths behave without requiring schema adjustments or new event types.

## 7) Support Infrastructure Requirements
- Reuse existing publisher utilities to emit `match.request` directly through `MessageBroker.publish_event`; no new routing keys or events required.
- Extend the current spy infrastructure (either new helper queues via [MessageSpy](../../tests/support/spy/message_spy.py:61) or small wrapper) to capture `match.result` and `matchings.process.completed` without schema changes.
- Create a `MatchingStateValidator` (adjacent to [DatabaseStateValidator](../../tests/support/validators/db_cleanup.py:321)) to count matches, inspect scores, and assert processed events using existing tables.
- Provide synthetic embedding/keypoint fixtures stored under `tests/mock_data/` (numpy arrays serialized as JSON or `.npy`) with deterministic values so acceptance thresholds can be hit pre-deterministically.
- Update documentation in `tests/support/fixtures/` to cover new matching environment setup procedures.

## 8) Failure Handling & Idempotency
- Validate duplicate detection by asserting `processed_events` row count changes exactly once per unique `event_id`.
- Simulate transient publishing failure by acknowledging event after DB insert (optional future enhancement) to ensure `matchings.process.completed` remains consistent.
- Confirm retries (if triggered) do not duplicate matches by inspecting `matches.match_id` uniqueness (UUID v4) and absence of duplicates for same product/video pair.

## 9) Execution & Tooling
- Target command: `pytest tests/integration/test_matching_phase_integration.py -v -k matching_phase --maxfail=1`.
- Introduce `@pytest.mark.matching` marker; register in `tests/integration/pytest.ini` alongside existing markers for consistent filtering.
- Keep runtime under 8 minutes by limiting dataset size (≤3 products × 1 video with ≤5 frames) and reusing seeded embeddings.
- Ensure tests tolerate cold-start stack by waiting on service health endpoints before publishing events.

## 10) Risks & Open Questions
- Deterministic embeddings: confirm stored vectors guarantee acceptance thresholds; otherwise provide helper to craft vectors aligned with [MatchAggregator](../../services/matcher/matching_components/match_aggregator.py:53).
- Broker timing: verify `main-api` publishes `match.request` fast enough; consider direct publish from tests when orchestrator timing causes flakiness, while still validating phase transitions via DB.
- Data volume in `matches`: cleaning up after tests must cascade to dependent tables to avoid FK violations (reuse logic from [CollectionPhaseCleanup._cleanup_table](../../tests/support/validators/db_cleanup.py:54)).
- Future scope: once evidence builder integration exists, confirm completion event triggers downstream workflow; track separately.

## Current Implementation Summary
**Status**: 🟡 Proposed — Transition coverage exists but dedicated matching-phase integration tests remain outstanding.

**Next Steps**:
1. Build deterministic matching fixtures (records + embeddings/keypoints) and new publisher/spy utilities.
2. Implement `test_matching_phase_integration.py` covering scenarios 6.1–6.4 with `@pytest.mark.matching`.
3. Wire markers into CI so the suite can gate releases alongside collection and feature extraction tests.
