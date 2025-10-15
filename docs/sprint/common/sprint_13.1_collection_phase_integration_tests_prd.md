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
  - Failure modes, retries, ordering variations, and video collection flows (TBD contracts) are out of scope to minimize test runtime.

## 2) Actors and Systems
- Services: main-api, dropship-product-finder.
- Broker/DB: RabbitMQ, Postgres/pgvector.
- Compose target: [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml)

## 3) Event Contracts and Data Surfaces
- In-scope contracts:
  - [products_collect_request.json](../../libs/contracts/contracts/schemas/products_collect_request.json)
  - [products_collections_completed.json](../../libs/contracts/contracts/schemas/products_collections_completed.json)
- Data access helpers:
  - [product_crud.py](../../libs/common-py/common_py/crud/product_crud.py)
  - [event_crud.py](../../libs/common-py/common_py/crud/event_crud.py)
- Out-of-scope (documented dependency to reduce cost):
  - videos.search.request and videos.collections.completed (no schemas in repo).

## 4) Environment, Configuration, Preconditions
- Stack up per [infra README](../../infra/pvm/README.md) using [docker-compose.dev.cpu.yml](../../infra/pvm/docker-compose.dev.cpu.yml).
- Run migrations with [run_migrations.py](../../scripts/run_migrations.py).
- Pytest alignment: [pytest.ini](../../pytest.ini), [services/pytest.ini](../../services/pytest.ini).
- Messaging conventions: [messaging.py](../../libs/common-py/common_py/messaging.py).
- Observability utilities: [metrics.py](../../libs/common-py/common_py/metrics.py), [health.py](../../libs/common-py/common_py/health.py).

## 5) Test Data and Fixtures
- Synthetic dataset location: [tests/mock_data](../../tests/mock_data)
  - Products: 3 items, 1 image metadata each; deterministic IDs and small placeholder assets.
  - Fixture loaders ensure consistent payloads; no external network calls.
- Do not read from [data](../../data/); use [tests/mock_data](../../tests/mock_data) exclusively.
- Spy queue: one ephemeral binding to the main exchange and target routing key; auto-delete post-test.
- DB cleanup: TRUNCATE affected product tables and event ledgers between runs.

## 6) Single Happy-Path Test (COL-01)
- COL-01 Products Collection — Happy Path (Combined, Minimal)
  - Setup:
    - Stack healthy; migrations applied; clean DB.
    - Load synthetic fixtures from [tests/mock_data](../../tests/mock_data).
    - Broker spy queue bound to products collection completed topic.
  - Trigger:
    - Publish [products_collect_request.json](../../libs/contracts/contracts/schemas/products_collect_request.json) with valid job_id for the minimal dataset.
  - Expected:
    - Exactly one [products_collections_completed.json](../../libs/contracts/contracts/schemas/products_collections_completed.json) observed.
    - Products persisted with expected fields via [product_crud.py](../../libs/common-py/common_py/crud/product_crud.py).
    - Logs include correlation_id and standardized fields; metrics increment events_total for products_collections_completed; health OK.
  - Idempotency (minimal check):
    - Re-publish the same request within the test → no duplicate completion or duplicate DB writes (validated via event ledger in [event_crud.py](../../libs/common-py/common_py/crud/event_crud.py)).

## 7) Observability Requirements
- Logs comply with [sprint_11_unified_logging_standards.md](./sprint_11_unified_logging_standards.md).
- Metrics: events_total for Collection using [metrics.py](../../libs/common-py/common_py/metrics.py).
- Health endpoints: healthy post-trigger using [health.py](../../libs/common-py/common_py/health.py).

## 8) Acceptance Criteria
- Schema conformance for request and completed events.
- DB state correctness for products; no duplicates on minimal idempotency check.
- Observability validated; DLQ remains empty.

## 9) Cost Minimization Notes
- Exclude video collection due to missing schemas and potential external dependencies.
- Single combined scenario, synthetic fixtures in [tests/mock_data](../../tests/mock_data), ephemeral spy queue, and aggressive teardown to minimize runtime.