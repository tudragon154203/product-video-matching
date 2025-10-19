# Sprint 13 — Feature Extraction Phase Integration Tests PRD (Happy Path + Critical)

Status: Plan-only; no code edits
Owners: QA/Infra
Related docs: [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml), [RUN.md](../../RUN.md), [infra README](../../infra/pvm/README.md), [sprint_12_unified_test_structure.md](./sprint_12_unified_test_structure.md)

## 1) Overview and Objectives
- Purpose: Validate the complete Feature Extraction phase happy path from masked inputs through embeddings and keypoints completion, with correct persistence and essential idempotency checks.
- Objectives:
  - End-to-end contract fidelity from masked batch inputs to feature completion events.
  - Correct persistence of embeddings and keypoints with referential integrity.
  - Basic idempotency assurance for re-delivery scenarios.
  - Observability coverage across the entire feature extraction pipeline.
  - Synthetic, consistent, mocked test data used exclusively from [tests/mock_data](../../tests/mock_data); do not read from [data](../../data/).
- Non-goals:
  - Comprehensive error scenarios, retries, and video embeddings completion (no schema) are out of scope.
  - Performance/stress testing not included.
  - Edge case testing minimized to maintain efficiency.

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
- Data access helpers:
  - [product_crud.py](../../libs/common-py/common_py/crud/product_crud.py)
  - [video_frame_crud.py](../../libs/common-py/common_py/crud/video_frame_crud.py)
- Out-of-scope:
  - video_embeddings_completed (no schema file present in repo).

## 4) Environment, Configuration, Preconditions
- Stack and migrations per [infra README](../../infra/pvm/README.md) and [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml).
- Run [run_migrations.py](../../scripts/run_migrations.py) before test execution.
- Pytest configs: [pytest.ini](../../pytest.ini), [services/pytest.ini](../../services/pytest.ini).
- Messaging conventions: [messaging.py](../../libs/common-py/common_py/messaging.py).
- Observability utilities: [metrics.py](../../libs/common-py/common_py/metrics.py), [health.py](../../libs/common-py/common_py/health.py).
- Models cache: fixtures in [tests/mock_data](../../tests/mock_data) provide minimal assets; no reliance on [model_cache](../../model_cache/) contents.

## 5) Test Data and Fixtures
- Synthetic dataset location: [tests/mock_data](../../tests/mock_data)
  - Ready product images: batch of 3 items with deterministic IDs
  - Ready keyframes: synthetic frames for one short video with deterministic sequence
  - Masked outputs: minimal placeholder assets for processing
- Do not read from [data](../../data/); use [tests/mock_data](../../tests/mock_data) exclusively.
- Spy queues: ephemeral and namespaced per event type; auto-delete after test.
- DB cleanup: TRUNCATE all updated tables and event ledgers between tests.

## 6) Test Scenarios

### FEAT-01 End-to-End Feature Extraction — Happy Path (Primary)
- Purpose: Validate complete pipeline from ready inputs through masking to feature completion.
- Setup:
  - Stack healthy; migrations applied; clean DB.
  - Load synthetic ready batch from [tests/mock_data](../../tests/mock_data) for images.
  - Load keyframes fixtures from [tests/mock_data](../../tests/mock_data).
  - Spy queues bound to all intermediate and completion events.
- Expected:
  - **Masking Phase**: Exactly one products_images_masked_batch and one video_keyframes_masked_batch observed.
  - **Extraction Phase**: Exactly one each of image_embeddings_completed, image_keypoints_completed, and video_keypoints_completed.
  - **Database Updates**: Masked paths updated, embeddings and keypoints persisted with referential integrity.
  - **Observability**: Logs standardized; metrics updated for all phases; health OK throughout.
- Duration target: < 5 minutes total.

### FEAT-02 Critical Idempotency — Feature Completion (Secondary)
- Purpose: Ensure no duplicate processing on feature completion event re-delivery.
- Setup:
  - Complete FEAT-01 setup to feature completion state.
  - Re-deliver one image_embeddings_completed event.
- Expected:
  - No duplicate embeddings inserted in database.
  - No additional metrics incremented beyond expected idempotency handling.
  - Logs show idempotency handling without errors.

### FEAT-03 Pipeline Continuity — Partial Batch Processing (Critical)
- Purpose: Validate pipeline handles mixed successful processing when some items fail.
- Setup:
  - Load batch with 2 valid items and 1 invalid/malformed item in [tests/mock_data](../../tests/mock_data).
- Expected:
  - Valid items processed completely through masking → feature extraction.
  - Invalid item gracefully handled without breaking pipeline.
  - Appropriate error logged but pipeline continues for valid items.
  - Final completion events reflect only successful processing.

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
- Synthetic fixtures from [tests/mock_data](../../tests/mock_data) ensure consistency and avoid external dependencies.
- Minimal test data (3 images, 1 video) keeps processing time reasonable.
- Focus on critical scenarios over comprehensive edge case coverage.

## 10) Success Metrics
- All tests pass consistently in CI environment.
- Total test execution time < 10 minutes.
- Zero flakiness across multiple runs.
- Full observability coverage validated.
- No data duplication in idempotency tests.