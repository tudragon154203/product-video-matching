# Sprint 13.2 — Ready/Masked Phase Integration Tests PRD (Happy Path Only)

Status: Plan-only; no code edits  
Owners: QA/Infra  
Related docs: [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml), [RUN.md](../../RUN.md), [infra README](../../infra/pvm/README.md), [sprint_12_unified_test_structure.md](./sprint_12_unified_test_structure.md)

## 1) Overview and Objectives
- Purpose: Validate the Ready/Masked phase happy path by masking product images and video keyframes, emitting correct masked batch events with accurate DB updates.
- Objectives:
  - Contract fidelity for masked batch events.
  - Correct DB path updates and batch counters.
  - Minimal idempotency assurance for re-delivery within the single scenario.
  - Observability coverage.
  - Synthetic, consistent, mocked test data used exclusively from [tests/mock_data](../../tests/mock_data); do not read from [data](../../data/).
- Non-goals:
  - Partial failures, out-of-order handling, and retries are out of scope to minimize runtime.

## 2) Actors and Systems
- Services: product-segmentor, video-crawler (masking step for keyframes).
- Broker/DB: RabbitMQ, Postgres/pgvector.
- Compose target: [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml)

## 3) Event Contracts and Data Surfaces
- In-scope contracts:
  - [products_images_ready_batch.json](../../libs/contracts/contracts/schemas/products_images_ready_batch.json)
  - [products_images_masked_batch.json](../../libs/contracts/contracts/schemas/products_images_masked_batch.json)
  - [video_keyframes_masked_batch.json](../../libs/contracts/contracts/schemas/video_keyframes_masked_batch.json)
- Data access helpers:
  - [product_crud.py](../../libs/common-py/common_py/crud/product_crud.py)
  - [video_frame_crud.py](../../libs/common-py/common_py/crud/video_frame_crud.py)
- Precondition:
  - videos.keyframes.ready.batch has no schema; treat as fixture-driven readiness sourced from [tests/mock_data](../../tests/mock_data).

## 4) Environment, Configuration, Preconditions
- Stack and migrations: [infra README](../../infra/pvm/README.md), [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml), [run_migrations.py](../../scripts/run_migrations.py).
- Pytest config: [pytest.ini](../../pytest.ini), [services/pytest.ini](../../services/pytest.ini).
- Messaging conventions: [messaging.py](../../libs/common-py/common_py/messaging.py).
- Observability utilities: [metrics.py](../../libs/common-py/common_py/metrics.py), [health.py](../../libs/common-py/common_py/health.py).

## 5) Test Data and Fixtures
- Synthetic dataset location: [tests/mock_data](../../tests/mock_data)
  - Products images: batch of 3 items; small placeholder assets; deterministic IDs.
  - Keyframes: synthetic frames for one short video; deterministic sequence and counts.
- Do not read from [data](../../data/); use [tests/mock_data](../../tests/mock_data) exclusively.
- Spy queues: ephemeral and namespaced; auto-delete after test.
- DB cleanup: TRUNCATE updated tables and event ledgers.

## 6) Single Happy-Path Test (MASK-01)
- MASK-01 Images and Keyframes Masking — Happy Path (Combined, Minimal)
  - Setup:
    - Stack healthy; migrations applied; clean DB.
    - Load synthetic ready batch from [tests/mock_data](../../tests/mock_data) for images.
    - Ensure keyframes exist via fixtures in [tests/mock_data](../../tests/mock_data).
  - Expected:
    - Exactly one [products_images_masked_batch.json](../../libs/contracts/contracts/schemas/products_images_masked_batch.json) observed for images.
    - Exactly one [video_keyframes_masked_batch.json](../../libs/contracts/contracts/schemas/video_keyframes_masked_batch.json) observed for keyframes.
    - DB masked paths updated for images via [product_crud.py](../../libs/common-py/common_py/crud/product_crud.py); keyframe updates applied via [video_frame_crud.py](../../libs/common-py/common_py/crud/video_frame_crud.py).
    - Logs standardized; metrics updated; health OK.
  - Idempotency (minimal check):
    - Re-deliver the same ready batch within the test → no duplicate side effects.

## 7) Observability Requirements
- Logs conform to [sprint_11_unified_logging_standards.md](./sprint_11_unified_logging_standards.md).
- Metrics: events_total for masked batches via [metrics.py](../../libs/common-py/common_py/metrics.py).
- Health: endpoints recover to healthy after transient work via [health.py](../../libs/common-py/common_py/health.py).

## 8) Acceptance Criteria
- Schema conformance for masked batch events.
- Accurate DB path updates and counters; no duplicates in minimal idempotency check.
- Observability verified; DLQ size 0.

## 9) Cost Minimization Notes
- Single combined scenario covering both images and keyframes minimizes total runtime and broker churn.
- Use synthetic fixtures from [tests/mock_data](../../tests/mock_data) to avoid external dependencies.