# Sprint 13 — Feature Extraction Phase Integration Tests PRD (Happy Path + Critical)

Status: ✅ Implemented - Integration tests exist and are functional
Owners: QA/Infra
Related docs: [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml), [RUN.md](../../RUN.md), [infra README](../../infra/pvm/README.md), [sprint_12_unified_test_structure.md](./sprint_12_unified_test_structure.md)

## 1) Overview and Objectives
- Purpose: Validate the complete Feature Extraction phase happy path from masked inputs through embeddings and keypoints completion, with correct persistence and essential idempotency checks.
- Objectives:
  - End-to-end contract fidelity from masked batch inputs to feature completion events.
  - Correct persistence of embeddings and keypoints with referential integrity.
  - Basic idempotency assurance for re-delivery scenarios.
  - Observability coverage across the entire feature extraction pipeline.
- Synthetic, consistent, mocked test data generated via [`tests/mock_data/test_data.py`](../../tests/mock_data/test_data.py); do not read from [data](../../data/).
- Non-goals:
  - Comprehensive error scenarios, retries, and performance/stress testing not included.
  - Edge case testing minimized to maintain efficiency.

## Implementation Status
- ✅ **Test Implementation**: [`tests/integration/test_feature_extraction_phase_integration.py`](../../tests/integration/test_feature_extraction_phase_integration.py) fully implements all scenarios
- ✅ **Test Data Support**: [`tests/mock_data/test_data.py`](../../tests/mock_data/test_data.py) provides synthetic data builders
- ✅ **Support Infrastructure**: Comprehensive test support in [`tests/support/`](../../tests/support/) including fixtures, publishers, spies, and validators
- ✅ **Event Schemas**: All required schemas exist, including [`video_embeddings_completed.json`](../../libs/contracts/contracts/schemas/video_embeddings_completed.json)
- ✅ **Test Execution**: Tests can be run with `pytest tests/integration/test_feature_extraction_phase_integration.py -v`

## 2) Actors and Systems
- Services: product-segmentor, video-crawler (masking), vision-embedding, vision-keypoint.
- Broker/DB: RabbitMQ, Postgres/pgvector.
- Compose target: [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml)

## 3) Event Contracts and Data Surfaces
- Input contracts:
  - [products_images_ready_batch.json](../../libs/contracts/contracts/schemas/products_images_ready_batch.json)
  - [video_keyframes_ready_batch.json] (treated as fixture-driven readiness)
- Intermediate contracts:
  - [products_images_masked_batch.json](../../libs/contracts/contracts/schemas/products_images_masked_batch.json)
  - [video_keyframes_masked_batch.json](../../libs/contracts/contracts/schemas/video_keyframes_masked_batch.json)
- Output contracts:
  - [image_embeddings_completed.json](../../libs/contracts/contracts/schemas/image_embeddings_completed.json)
  - [image_keypoints_completed.json](../../libs/contracts/contracts/schemas/image_keypoints_completed.json)
  - [video_keypoints_completed.json](../../libs/contracts/contracts/schemas/video_keypoints_completed.json)
  - [video_embeddings_completed.json](../../libs/contracts/contracts/schemas/video_embeddings_completed.json) (now available)
- Data access helpers:
  - [product_crud.py](../../libs/common-py/common_py/crud/product_crud.py)
  - [video_frame_crud.py](../../libs/common-py/common_py/crud/video_frame_crud.py)

## 4) Environment, Configuration, Preconditions
- Stack and migrations per [infra README](../../infra/pvm/README.md) and [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml).
- Run [run_migrations.py](../../scripts/run_migrations.py) before test execution.
- Pytest configs: [pytest.ini](../../pytest.ini), [services/pytest.ini](../../services/pytest.ini).
- Messaging conventions: [messaging.py](../../libs/common-py/common_py/messaging.py).
- Observability utilities: [metrics.py](../../libs/common-py/common_py/metrics.py), [health.py](../../libs/common-py/common_py/health.py).
- Models cache: fixtures produced by the shared builders provide minimal assets; no reliance on [model_cache](../../model_cache/) contents.

## 5) Test Data and Fixtures
- Synthetic dataset builders: [`tests/mock_data/test_data.py`](../../tests/mock_data/test_data.py)
  - Ready product images: batch of 3 items with deterministic IDs using existing test files
  - Ready keyframes: synthetic frames for one short video with deterministic sequence
  - Masked outputs: minimal placeholder assets for processing (uses same file paths for testing)
- Test support infrastructure: [`tests/support/`](../../tests/support/)
  - Fixtures: [`tests/support/fixtures/feature_extraction_fixtures.py`](../../tests/support/fixtures/feature_extraction_fixtures.py)
  - Setup utilities: [`tests/support/fixtures/feature_extraction_setup.py`](../../tests/support/fixtures/feature_extraction_setup.py)
  - Event publishing: [`tests/support/publisher/event_publisher.py`](../../tests/support/publisher/event_publisher.py)
  - Message spying: [`tests/support/spy/`](../../tests/support/spy/)
  - Database management: [`tests/support/validators/`](../../tests/support/validators/)
- Do not read from [data](../../data/); rely on the dynamic builders exclusively.
- Spy queues: ephemeral and namespaced per event type; auto-delete after test.
- DB cleanup: TRUNCATE all updated tables and event ledgers between tests.

## 6) Test Scenarios

### FEAT-01 End-to-End Feature Extraction — Happy Path (Primary) ✅ Implemented
- **Implementation**: `test_comprehensive_feature_extraction_end_to_end()` in [`tests/integration/test_feature_extraction_phase_integration.py`](../../tests/integration/test_feature_extraction_phase_integration.py)
- Purpose: Validate complete pipeline from ready inputs through masking to feature completion with idempotency testing.
- Setup:
  - Stack healthy; migrations applied; clean DB.
  - Use `build_product_dataset()` and `build_video_dataset()` for synthetic data.
  - Comprehensive test environment setup via [`feature_extraction_test_environment`](../../tests/support/fixtures/feature_extraction_fixtures.py) fixture.
  - Spy queues bound to all intermediate and completion events via [`feature_extraction_spy.py`](../../tests/support/spy/feature_extraction_spy.py).
- Expected:
  - **Masking Phase**: products_images_masked_batch and video_keyframes_masked_batch observed (with timeout handling).
  - **Extraction Phase**: image_embeddings_completed, image_keypoints_completed, and video_keypoints_completed observed.
  - **Database Updates**: Validated via [`validate_feature_extraction_completed()`](../../tests/support/fixtures/feature_extraction_setup.py).
  - **Idempotency Testing**: Built into the main test via [`run_idempotency_test()`](../../tests/support/fixtures/feature_extraction_setup.py).
  - **Observability**: Timeout-tolerant validation with comprehensive progress reporting.
- Duration target: < 5 minutes total (implemented with 120-second test timeout).

### FEAT-02 Critical Idempotency — Feature Completion (Secondary) ✅ Implemented
- **Implementation**: Integrated into FEAT-01 main test via `run_idempotency_test()` function.
- Purpose: Ensure no duplicate processing on feature completion event re-delivery.
- Setup:
  - Complete FEAT-01 setup to feature completion state.
  - Re-delivery testing built into [`run_idempotency_test()`](../../tests/support/fixtures/feature_extraction_setup.py).
- Expected:
  - No duplicate embeddings inserted in database.
  - No additional metrics incremented beyond expected idempotency handling.
  - Logs show idempotency handling without errors.

### Additional Phase-Specific Tests ✅ Implemented
- **Masking Phase Test**: `test_masking_phase_only()` - Focuses specifically on masking/background removal
- **Embeddings Phase Test**: `test_embeddings_phase_only()` - Tests CLIP embeddings generation phase
- **Keypoints Phase Test**: `test_keypoints_phase_only()` - Tests traditional CV keypoint extraction phase
- All individual phase tests use the same comprehensive fixture and support infrastructure

### FEAT-03 Pipeline Continuity — Partial Batch Processing (Critical) ⚠️ Not Yet Implemented
- Purpose: Validate pipeline handles mixed successful processing when some items fail.
- Setup:
  - Build partial batches using helper functions to mix valid/invalid items.
- Expected:
  - Valid items processed completely through masking → feature extraction.
  - Invalid item gracefully handled without breaking pipeline.
  - Appropriate error logged but pipeline continues for valid items.
  - Final completion events reflect only successful processing.
- **Status**: Scenario described in PRD but not yet implemented in test suite.

## 7) Observability Requirements
- Logs conform to [sprint_11_unified_logging_standards.md](./sprint_11_unified_logging_standards.md) across all services.
- Metrics via [metrics.py](../../libs/common-py/common_py/metrics.py):
  - events_total for all event types (masked batches, feature completions)
  - feature_counts for embeddings and keypoints processed
  - processing_duration_seconds for pipeline timing
- Health: endpoints remain healthy via [health.py](../../libs/common-py/common_py/health.py) during and after processing.

## 8) Acceptance Criteria
- Schema conformance for all in-scope events (masked batches and feature completions).
- End-to-end data flow from ready inputs to feature completion working correctly.
- Persistence and referential integrity for all database updates.
- Critical idempotency scenarios handled without duplicate data.
- Observability validated across all pipeline stages.
- DLQ remains empty for happy path scenarios.

## 9) Cost and Efficiency Notes
- Combined scenarios reduce total runtime vs. separate phase tests.
- Synthetic fixtures from the shared builders ensure consistency and avoid external dependencies.
- Minimal test data (3 images, 1 video) keeps processing time reasonable.
- Focus on critical scenarios over comprehensive edge case coverage.

## 10) Success Metrics
- ✅ **Test Implementation**: All primary scenarios implemented with comprehensive test infrastructure
- ✅ **Test Execution**: Tests can be run with `pytest tests/integration/test_feature_extraction_phase_integration.py -v`
- ⏳ **CI Validation**: Tests should pass consistently in CI environment (needs validation)
- ⏳ **Performance Target**: Total test execution time < 10 minutes (needs measurement)
- ⏳ **Reliability**: Zero flakiness across multiple runs (needs validation)
- ✅ **Coverage**: Full observability coverage validated through test infrastructure
- ✅ **Idempotency**: Data duplication prevention implemented and tested

## Current Implementation Summary
**Status**: 🟢 **Largely Complete** - Core end-to-end functionality implemented with comprehensive test infrastructure. Only partial batch processing scenario remains unimplemented.

**Next Steps**:
1. Validate test execution in CI environment
2. Implement FEAT-03 partial batch processing scenario if needed
3. Measure and optimize test execution time
4. Add any missing edge case coverage based on runtime behavior
