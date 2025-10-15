# Sprint 13.1 — Collection Phase Integration Tests PRD (Happy Path Only)

Status: Plan-only; no code edits  
Owners: QA/Infra  
Related docs: [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml), [RUN.md](../../RUN.md), [infra README](../../infra/pvm/README.md), [sprint_12_unified_test_structure.md](./sprint_12_unified_test_structure.md)

## 1) Overview and Objectives
- Purpose: Validate the Collection phase happy path that ingests product discovery requests and emits the completed collection event, with correct persistence and observability.
- Objectives:
  - Contract fidelity for request and completion events.
  - State correctness in Postgres for products.
  - Minimal idempotency assurance by suppressing duplicates within the single scenario.
  - Observability via standardized logs, metrics, and health.
  - Synthetic, consistent, mocked test data used exclusively from [tests/mock_data](../../tests/mock_data); do not read from [data](../../data/).
- Non-goals:
  - Failure modes, retries, and ordering variations are out of scope to minimize test runtime. Video collection flow is in-scope with a cap of 2 videos to control runtime.

## 2) Actors and Systems
- Services: main-api, dropship-product-finder, video-crawler.
- Broker/DB: RabbitMQ, Postgres/pgvector.
- Compose target: [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml)

## 3) Event Contracts and Data Surfaces
- In-scope contracts:
  - [products_collect_request.json](../../libs/contracts/contracts/schemas/products_collect_request.json)
  - [products_collections_completed.json](../../libs/contracts/contracts/schemas/products_collections_completed.json)
  - [videos_search_request.json](../../libs/contracts/contracts/schemas/videos_search_request.json)
  - [videos_collections_completed.json](../../libs/contracts/contracts/schemas/videos_collections_completed.json)
- Data access helpers:
  - [product_crud.py](../../libs/common-py/common_py/crud/product_crud.py)
  - [video_crud.py](../../libs/common-py/common_py/crud/video_crud.py)
  - [event_crud.py](../../libs/common-py/common_py/crud/event_crud.py)

## 4) Environment, Configuration, Preconditions
- Stack up per [infra README](../../infra/pvm/README.md) using [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml).
- Run migrations with [run_migrations.py](../../scripts/run_migrations.py).
- Pytest alignment: [pytest.ini](../../pytest.ini), [services/pytest.ini](../../services/pytest.ini).
- Messaging conventions: [messaging.py](../../libs/common-py/common_py/messaging.py).
- Observability utilities: [metrics.py](../../libs/common-py/common_py/metrics.py), [health.py](../../libs/common-py/common_py/health.py).

## 5) Test Data and Fixtures
- Synthetic dataset location: [tests/mock_data](../../tests/mock_data)
  - Products: 3 items, 1 image metadata each; deterministic IDs and small placeholder assets.
  - Videos: cap at 2 items per test; deterministic or preselected IDs; small placeholder metadata; avoid external network calls where feasible.
  - Fixture loaders ensure consistent payloads; no external network calls where feasible.
- Do not read from [data](../../data/); use [tests/mock_data](../../tests/mock_data) exclusively.
- Spy queues: ephemeral queue(s) bound to products and videos collection completed routing keys; auto-delete post-test.
- DB cleanup: TRUNCATE affected product tables, video tables (e.g., videos, video_frames), and event ledgers between runs.

## 6) Single Happy-Path Test
- Products & Videos Collection — Happy Path (Combined, Minimal)
  - Setup:
    - Stack healthy; migrations applied; clean DB.
    - Load synthetic fixtures from [tests/mock_data](../../tests/mock_data).
    - Broker spy queues bound to products and videos collection completed topics.
  - Trigger:
    - Publish [products_collect_request.json](../../libs/contracts/contracts/schemas/products_collect_request.json) with valid job_id and correlation_id for the minimal dataset.
    - Publish [videos_search_request.json](../../libs/contracts/contracts/schemas/videos_search_request.json) with the same job_id and correlation_id; cap at 2 videos.
  - Expected:
    - Exactly one [products_collections_completed.json](../../libs/contracts/contracts/schemas/products_collections_completed.json) observed within 10s.
    - Exactly one [videos_collections_completed.json](../../libs/contracts/contracts/schemas/videos_collections_completed.json) observed within 10s.
    - Products persisted with expected fields via [product_crud.py](../../libs/common-py/common_py/crud/product_crud.py).
    - Videos persisted with expected fields via [video_crud.py](../../libs/common-py/common_py/crud/video_crud.py).
    - Logs include correlation_id and standardized fields; metrics increment events_total for products_collections_completed and videos_collections_completed; health OK; DLQ empty.
  - Idempotency (minimal check):
    - Re-publish the same requests within the test → no duplicate completion events or duplicate DB writes for either domain (validated via event ledger in [event_crud.py](../../libs/common-py/common_py/crud/event_crud.py)).

## 7) Observability Requirements
- Logs comply with [sprint_11_unified_logging_standards.md](./sprint_11_unified_logging_standards.md).
- Metrics: events_total counters for products_collections_completed and videos_collections_completed using [metrics.py](../../libs/common-py/common_py/metrics.py).
- Health endpoints: healthy post-trigger using [health.py](../../libs/common-py/common_py/health.py).

## 8) Acceptance Criteria
- Schema conformance for request and completed events (products and videos).
- DB state correctness for products and videos; no duplicates on minimal idempotency check across both domains.
- Observability validated; DLQ remains empty.

## 9) Cost Minimization Notes
- Include video collection with a cap of 2 videos per test to limit runtime; leverage existing schemas.
- Single combined scenario, synthetic fixtures in [tests/mock_data](../../tests/mock_data), ephemeral spy queues, 10s per-event timeouts, and aggressive teardown to minimize runtime.