# Sprint 13.3 — Feature Extraction Phase Integration Tests PRD (Happy Path Only)

Status: Plan-only; no code edits  
Owners: QA/Infra  
Related docs: [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml), [RUN.md](../../RUN.md), [infra README](../../infra/pvm/README.md), [sprint_12_unified_test_structure.md](./sprint_12_unified_test_structure.md)

## 1) Overview and Objectives
- Purpose: Validate the Feature Extraction phase happy path for embeddings and keypoints completions, with correct persistence and minimal idempotency checks.
- Objectives:
  - Contract fidelity for feature completion events.
  - Persistence of embeddings/keypoints with referential integrity.
  - Minimal idempotency assurance for re-delivery within the single scenario.
  - Observability coverage.
  - Synthetic, consistent, mocked test data used exclusively from [tests/mock_data](../../tests/mock_data); do not read from [data](../../data/).
- Non-goals:
  - Error handling, retries, and video embeddings completion (no schema) are out of scope to minimize runtime.

## 2) Actors and Systems
- Services: vision-embedding, vision-keypoint.
- Broker/DB: RabbitMQ, Postgres/pgvector.
- Compose target: [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml)

## 3) Event Contracts and Data Surfaces
- In-scope contracts:
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
- Run [run_migrations.py](../../scripts/run_migrations.py).
- Pytest configs: [pytest.ini](../../pytest.ini), [services/pytest.ini](../../services/pytest.ini).
- Messaging conventions: [messaging.py](../../libs/common-py/common_py/messaging.py).
- Observability utilities: [metrics.py](../../libs/common-py/common_py/metrics.py), [health.py](../../libs/common-py/common_py/health.py).
- Models cache and masked assets: fixtures in [tests/mock_data](../../tests/mock_data) provide minimal assets or mocks; no reliance on [model_cache](../../model_cache/) contents for test stability.

## 5) Test Data and Fixtures
- Synthetic fixtures location: [tests/mock_data](../../tests/mock_data)
  - Masked images and keyframes ready from fixtures; deterministic counts and identifiers.
- Do not read from [data](../../data/); use [tests/mock_data](../../tests/mock_data) exclusively.
- Spy queues: ephemeral per event type; auto-delete after test.
- DB cleanup: TRUNCATE embeddings/keypoints tables and event ledgers.

## 6) Single Happy-Path Test (FEAT-01)
- FEAT-01 Features Completion — Happy Path (Combined, Minimal)
  - Setup:
    - Stack healthy; migrations applied; clean DB.
    - Load masked images and keyframes from fixtures in [tests/mock_data](../../tests/mock_data).
    - Spy queues bound to image_embeddings_completed, image_keypoints_completed, and video_keypoints_completed topics.
  - Expected:
    - Exactly one [image_embeddings_completed.json](../../libs/contracts/contracts/schemas/image_embeddings_completed.json) observed.
    - Exactly one [image_keypoints_completed.json](../../libs/contracts/contracts/schemas/image_keypoints_completed.json) observed.
    - Exactly one [video_keypoints_completed.json](../../libs/contracts/contracts/schemas/video_keypoints_completed.json) observed.
    - Embeddings and keypoints persisted with referential integrity using [product_crud.py](../../libs/common-py/common_py/crud/product_crud.py) and [video_frame_crud.py](../../libs/common-py/common_py/crud/video_frame_crud.py).
    - Logs standardized; metrics updated; health OK.
  - Idempotency (minimal check):
    - Re-deliver completion for one event within the test → no duplicate side effects.

## 7) Observability Requirements
- Logs conform to [sprint_11_unified_logging_standards.md](./sprint_11_unified_logging_standards.md).
- Metrics: events_total and feature_counts via [metrics.py](../../libs/common-py/common_py/metrics.py).
- Health: healthy post-completion via [health.py](../../libs/common-py/common_py/health.py).

## 8) Acceptance Criteria
- Schema conformance for all in-scope completion events.
- Persistence and referential integrity for embeddings and keypoints; no duplicates on minimal idempotency check.
- Observability validated; DLQ remains empty.

## 9) Cost Minimization Notes
- Single combined scenario across three completion events reduces total runtime and broker churn.
- Use synthetic fixtures from [tests/mock_data](../../tests/mock_data) to avoid external dependencies and ensure consistency.