# Sprint 13.3 — Matching Phase Integration Tests PRD (Happy Path + Critical)

Status: ✅ Implemented – Matching-phase coverage complete  
Owners: QA/Infra  
Related docs: [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml), [RUN.md](../../RUN.md), [infra README](../../infra/pvm/README.md), [sprint_12_unified_test_structure.md](./sprint_12_unified_test_structure.md), [sprint_13.2_feature_extraction_phase_integration_tests_prd.md](./sprint_13.2_feature_extraction_phase_integration_tests_prd.md), [sprint_2_matcher_microservice_implementation.md](../matcher/sprint_2_matcher_microservice_implementation.md), [test_matching_phase_integration.py](../../tests/integration/test_matching_phase_integration.py)

## 1) Overview and Objectives
- Purpose: 🟡 Deliver an end-to-end matching phase integration suite that exercises `match.request` ingestion through `match.request.completed`, validating persistence and emissions across the live stack.
- Objectives:
  - 🟡 Contract fidelity for ingress/egress events (`match.request`, `match.result`, `match.request.completed`) and supporting DB writes.
  - 🟡 Validate job transitions to `evidence` driven by [PhaseTransitionManager._process_matching_phase](../../services/main-api/services/phase/phase_transition_manager.py:115).
  - 🟡 Prove matcher idempotency by replaying identical events and asserting [EventCRUD.record_event](../../libs/common-py/common_py/crud/event_crud.py:8) suppresses duplicates.
- Non-goals:
  - ❌ DLQ stress tests or long-run retry backoff scenarios.
  - ❌ Load/performance benchmarking of vector search or scoring components.
  - ❌ Evidence builder rendering validations (covered in downstream evidence-phase suite).

## Implementation Status
- ✅ Transition coverage exists: [test_feature_extraction_to_matching_transition.py](../../tests/integration/test_feature_extraction_to_matching_transition.py:28) validates feature extraction completion triggers `match.request` and phase promotion to `matching`.
- ✅ Integration test suite implemented: [test_matching_phase_integration.py](../../tests/integration/test_matching_phase_integration.py) drives [MatcherService.handle_match_request](../../services/matcher/services/service.py:43) against live Postgres/RabbitMQ.
- ✅ Test data builders provide deterministic embeddings/keypoints via [build_matching_test_dataset](../../tests/mock_data/test_data.py) and [build_low_similarity_matching_dataset](../../tests/mock_data/test_data.py) for consistent match scoring.
- ✅ Comprehensive assertions validate [MatchCRUD.create_match](../../libs/common-py/common_py/crud/match_crud.py:9), [processed_events](../../infra/migrations/versions/005_add_processed_events_table.py:18), `match.result` routing, and phase transitions.

## 2) Actors and Systems
- 🟡 `matcher` service: entry point [MatcherHandler.handle_match_request](../../services/matcher/handlers/matcher_handler.py:24) delegates to [MatcherService.handle_match_request](../../services/matcher/services/service.py:43) which persists matches and publishes completion.
- 🟡 `main-api`: phase orchestration via [PhaseTransitionManager.check_phase_transitions](../../services/main-api/services/phase/phase_transition_manager.py:15) and `_process_matching_phase` to promote jobs on `match.request.completed`.
- 🟡 RabbitMQ `product_video_matching` topic exchange observed through [MessageSpy](../../tests/support/spy/message_spy.py:61) for `match.request`, `match.result`, and completion events.
- 🟡 Postgres surfaces: `products`, `product_images`, `videos`, `video_frames`, `matches`, `processed_events`, and `phase_events` defined in [001_initial_schema](../../infra/migrations/versions/001_initial_schema.py:108) and [005_processed_events](../../infra/migrations/versions/005_add_processed_events_table.py:18).
- 🟡 Observability: out of scope for this sprint; rely on existing logging without additional validation.

## 3) Event Contracts and Data Surfaces
- Input contract: [match_request.json](../../libs/contracts/contracts/schemas/match_request.json) published by `main-api`.
- Output contracts:
  - [match_result.json](../../libs/contracts/contracts/schemas/match_result.json) emitted per accepted product/video pair.
  - [match_request_completed.json](../../libs/contracts/contracts/schemas/match_request_completed.json) emitted once per job.
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
- ✅ Extended [tests/mock_data/test_data.py](../../tests/mock_data/test_data.py:16) with `build_matching_test_dataset` and `build_low_similarity_matching_dataset` helpers that attach deterministic `emb_rgb`, `emb_gray`, and `kp_blob_path` values to products and frames.
- ✅ Combined dataset builders return product/video records plus ready-to-publish `match_request` events with expected results for validation.
- ✅ Implemented `matching_test_environment` fixture in [test_matching_phase_integration.py](../../tests/integration/test_matching_phase_integration.py:52) composing:
  - `MessageSpy` queues for `match.result` and `match.request.completed` topics.
  - Database cleanup via `cleanup_test_database_state` scoped to test job IDs.
  - `DatabaseStateValidator` assertions for matches, processed events, and job phase transitions.
  - `MatchingEventPublisher` with `publish_match_request` helper for event emission.
- ✅ Setup helpers `setup_comprehensive_matching_database_state`, `setup_low_similarity_matching_database_state`, and `setup_partial_asset_matching_database_state` seed prerequisite data for each test scenario.

## 6) Proposed Test Suite

### 6.1) Matching — Full Pipeline With Acceptable Pair ✅
- **Implementation**: [test_matching_full_pipeline_acceptable_pair](../../tests/integration/test_matching_phase_integration.py:100)
- **Setup**: Seeds job with 3 products and 5 frames using `build_matching_test_dataset` with deterministic embeddings and keypoints. Verifies prerequisite data insertion before proceeding.
- **Execution**: Publishes schema-valid `match.request` with unique `event_id`; waits 2 seconds for processing and captures events via message spies.
- **Validations**:
  - ✅ Asserts `match.result` payload structure matches expected result with `score_pair` ≥ 0.8 (MATCH_BEST_MIN threshold).
  - ✅ Confirms `matches` table contains persisted rows with correct job_id, score ≥ 0.8, and status "accepted".
  - ✅ Validates exactly one `match.request.completed` event fired.
  - ✅ Verifies job phase advanced to "evidence" via `DatabaseStateValidator.assert_job_phase`.
  - ✅ Checks `processed_events` contains the dispatched `event_id`.
- **Notes**: Uses existing routing keys and tables without schema changes.

### 6.2) Matching — Zero Acceptable Matches (Fail-Gating) ✅
- **Implementation**: [test_matching_zero_acceptable_matches](../../tests/integration/test_matching_phase_integration.py:177)
- **Setup**: Seeds dataset with low similarity embeddings via `build_low_similarity_matching_dataset` to ensure scores fall below acceptance thresholds.
- **Execution**: Publishes `match.request`; waits for `match.request.completed` without expecting `match.result`.
- **Validations**:
  - ✅ Asserts zero `match.result` events captured by spy.
  - ✅ Confirms `matches` table has zero inserts for the test job.
  - ✅ Validates completion event still occurs (exactly one event).
  - ✅ Verifies job still advances to "evidence" phase despite zero matches.
- **Notes**: Confirms zero-match path completes successfully without errors, aligning with fail-gating requirements.

### 6.3) Matching — Idempotent Re-delivery ✅
- **Implementation**: [test_matching_idempotent_redelivery](../../tests/integration/test_matching_phase_integration.py:213)
- **Setup**: Seeds standard dataset with 2 products and 3 frames; uses specific `event_id` "idempotency_test_event_001" for duplicate testing.
- **Execution**: Publishes the same `match.request` twice with 0.5s delay between publishes. Then publishes a new event with different `event_id` to verify new work still processes.
- **Validations**:
  - ✅ Captures initial match count and DB match count from first processing.
  - ✅ Asserts `processed_events` contains event_id exactly once.
  - ✅ Validates exactly one completion event for the job (not "at least one").
  - ✅ Confirms duplicate delivery didn't create additional matches (exact count comparison).
  - ✅ Verifies new event with different `event_id` produces same number of matches.
  - ✅ Confirms total of 2 processed_events entries exist (one per unique event_id).
- **Notes**: Comprehensive idempotency validation with exact count assertions prevents duplicate processing.

### 6.4) Matching — Partial Asset Availability (Fallback Coverage) ✅
- **Implementation**: [test_matching_partial_asset_fallback](../../tests/integration/test_matching_phase_integration.py:277)
- **Setup**: Seeds dataset with 2 products and 3 frames, then modifies second product to have `kp_blob_path = None` to trigger fallback behavior.
- **Execution**: Publishes `match.request`; relies on embeddings-only scoring when keypoints unavailable.
- **Validations**:
  - ✅ Validates completion event occurs despite missing keypoints (at least one event).
  - ✅ Confirms job advances to "evidence" phase.
  - ✅ Verifies processing completes without errors when fallback path is triggered.
  - ✅ Ensures consistent results based on available assets (embeddings-only scoring).
- **Notes**: Test validates fallback path robustness without requiring schema changes. Future enhancement could add log inspection for "Missing keypoint blob path" messages.

## 7) Support Infrastructure Requirements ✅
- ✅ Implemented `MatchingEventPublisher` in [event_publisher.py](../../tests/support/publisher/event_publisher.py) with `publish_match_request` method for direct event emission.
- ✅ Extended `MessageSpy` infrastructure to capture `match.result` and `match.request.completed` events via dedicated spy queues created in `matching_test_environment` fixture.
- ✅ Reused existing `DatabaseStateValidator` for matches, processed events, and job phase assertions without requiring new validator classes.
- ✅ Implemented synthetic embedding/keypoint fixtures in [test_data.py](../../tests/mock_data/test_data.py) with deterministic values ensuring consistent acceptance threshold behavior.
- ✅ Created setup helpers in [matching_phase_setup.py](../../tests/support/fixtures/matching_phase_setup.py) including `setup_comprehensive_matching_database_state`, `setup_low_similarity_matching_database_state`, `setup_partial_asset_matching_database_state`, and `cleanup_test_database_state`.

## 8) Failure Handling & Idempotency ✅
- ✅ Validates duplicate detection by asserting `processed_events` row count changes exactly once per unique `event_id` in idempotency test.
- ✅ Confirms exact match counts remain unchanged when duplicate events are published (no additional matches created).
- ✅ Verifies completion events occur exactly once per unique event (changed from "at least once" to exact count validation).
- ✅ Tests that new events with different `event_id` still process normally, proving idempotency doesn't block legitimate work.
- Future enhancement: Simulate transient publishing failures to test retry behavior without duplication.

## 9) Execution & Tooling ✅
- ✅ Target command: `pytest tests/integration/test_matching_phase_integration.py -v --maxfail=1`.
- ✅ Implemented `@pytest.mark.matching` and `@pytest.mark.integration` markers at module level via `pytestmark`.
- ✅ Runtime optimized with limited dataset sizes (3 products × 5 frames for happy path, 2 products × 3 frames for other scenarios).
- ✅ Uses 2-second wait periods for event processing with message spy capture.
- ✅ Leverages `clean_database` fixture for test isolation and cleanup.
- Note: Tests assume services are running; consider adding health check waits for cold-start tolerance.

## 10) Risks & Resolved Issues
- ✅ Deterministic embeddings: Implemented via `build_matching_test_dataset` and `build_low_similarity_matching_dataset` with controlled vector values.
- ✅ Broker timing: Tests publish `match.request` directly via `MatchingEventPublisher`, avoiding orchestrator timing dependencies while still validating phase transitions.
- ✅ Data cleanup: `clean_database` fixture handles cascading deletes for matches, video_frames, product_images, and related tables.
- ✅ Debug output: Removed debug print statements from tests for cleaner output.
- ✅ Exact assertions: Enhanced idempotency test with exact count validations instead of "at least" checks.
- Future scope: Evidence builder integration to validate downstream workflow triggering from completion events.

## Current Implementation Summary
**Status**: ✅ Complete — All four matching-phase integration test scenarios implemented and validated.

**Implemented Components**:
1. ✅ Test suite: [test_matching_phase_integration.py](../../tests/integration/test_matching_phase_integration.py) with all 4 scenarios (6.1-6.4).
2. ✅ Test data builders: `build_matching_test_dataset` and `build_low_similarity_matching_dataset` in [test_data.py](../../tests/mock_data/test_data.py).
3. ✅ Setup fixtures: `matching_test_environment` with message spies, validators, and publishers.
4. ✅ Database setup helpers: `setup_comprehensive_matching_database_state`, `setup_low_similarity_matching_database_state`, `setup_partial_asset_matching_database_state`.
5. ✅ Event publisher: `MatchingEventPublisher` with `publish_match_request` method.
6. ✅ Test markers: `@pytest.mark.matching` and `@pytest.mark.integration` applied at module level.

**Test Coverage**:
- ✅ Happy path with acceptable matches and phase transition
- ✅ Zero matches scenario with fail-gating behavior
- ✅ Idempotent re-delivery with exact count validations
- ✅ Partial asset availability with fallback scoring

**Next Steps**:
1. Consider replacing hardcoded `asyncio.sleep(2.0)` with polling utilities for more reliable timing.
2. Add log inspection to partial asset test for explicit fallback path validation.
3. Wire test suite into CI pipeline to gate releases alongside other phase tests.
