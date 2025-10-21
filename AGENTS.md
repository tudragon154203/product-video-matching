# Repository Guidelines

## Project Structure & Module Organization
- `services/`: Python microservices. Key services: `main-api` (orchestration), `results-api` (read API), `vision-embedding`, `vision-keypoint`, `video-crawler`, `matcher`, `evidence-builder`, `dropship-product-finder`.
- `libs/`: shared code. Use `libs/common-py/common_py/*` via `PYTHONPATH` in Compose.
- `infra/pvm/`: Docker Compose env (`docker-compose.dev.yml`) and `.env` files.
- `tests/`: integration/system tests (requires infra up). Fixtures in `tests/conftest.py`.
- `scripts/`: utilities like `run_migrations.py`, `seed.py`.
- `data/` and `model_cache/`: local volumes (gitignored) for datasets, models.
- Docs: `README.md`, `RUN.md`, `API.md`, `CONTRACTS.md`.

## Build, Test, and Development Commands
- Bring up dev stack: `docker compose -f infra/pvm/docker-compose.dev.yml up -d --build` (PowerShell: `./up-dev.ps1`).
- Run migrations: `python scripts/run_migrations.py upgrade` (PowerShell: `./migrate.ps1`).
- Seed sample data: `python scripts/seed.py`.
- Tail logs: `docker compose -f infra/pvm/docker-compose.dev.yml logs -f <service>`.
- Stop stack: `docker compose -f infra/pvm/docker-compose.dev.yml down` (PowerShell: `./down-dev.ps1`).

## Coding Style & Naming Conventions
- Python 3.10+. Indentation: 4 spaces; follow PEP 8; prefer type hints.
- Names: snake_case (modules/functions), PascalCase (classes), UPPER_SNAKE_CASE (constants).
- Service layout: each service has `Dockerfile`, `main.py`, `config_loader.py`, `handlers/`, `services/`.
- Tests: `test_*.py`. Keep tests close to features and in root `tests/` for integrations.
- `__init__.py` files should be empty to avoid namespace pollution and import issues.

## Testing Guidelines
- Install test deps: `pip install -r requirements-test.txt`.
- Bring infra up before integration tests.
- Run tests: Always navigate to the microservice directory first:
  ```cmd
  cd services\your-microservice-name
  python -m pytest tests\ -v
  ```
  Use `-k <expr>` to filter tests. Aim for meaningful coverage on core flows.
- Use small fixtures; avoid large media in Git.

## Commit & Pull Request Guidelines
- Commits: concise, imperative summaries; group related changes. Conventional Commits optional (not consistently used in history).
- PRs: include purpose, linked issues (`Closes #123`), test steps, and relevant logs/screenshots.
- Checks: green CI, smoke tests pass (`./smoke.ps1`) before merge; prefer squash-merge.

## Security & Configuration Tips
- Never commit secrets. Copy `infra/pvm/.env.example` → `infra/pvm/.env`; per‑service `.env.example` → `.env`.
- Use Git LFS for large artifacts (videos/models) when versioning.
- Ports: Postgres on `5435`, RabbitMQ UI on `15672`. Adjust in Compose if needed.

## Architecture Overview
- Event‑driven pipeline over RabbitMQ. Postgres + pgvector for storage/search. `main-api` orchestrates jobs; workers emit artifacts consumed by `matcher` and served by `results-api`.

