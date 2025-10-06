<!--
Sync Impact Report:
- Version change: 1.7.0 → 1.7.1
- List of modified principles: VII. Quality Assurance (added autopep8 formatting requirement)
- Added sections: None
- Removed sections: None
- Templates requiring updates:
    - .specify/templates/tasks-template.md: ✅ updated
    - .specify/templates/plan-template.md: ⚠ pending
    - .specify/templates/spec-template.md: ⚠ pending
    - .specify/templates/commands/*.md: ⚠ pending
    - README.md: ⚠ pending
    - RUN.md: ⚠ pending
- Follow-up TODOs: TODO(RATIFICATION_DATE): Original adoption date unknown
-->
# Product-Video Matching System Constitution

## Core Principles

### I. Microservice Structure
All microservices MUST adhere to a standardized structure: `app/main.py` (entry point), `handlers/` (RabbitMQ event handlers), `services/` (business logic), `config_loader.py` (environment configuration), `Dockerfile`, and a service-specific `.env` file. This ensures consistency, maintainability, and ease of onboarding for new developers.

### II. Event Contracts
All inter-service communication via RabbitMQ MUST conform to defined event contracts. Events in `libs/contracts/contracts/schemas/` MUST utilize JSON schema validation. Routing keys MUST follow a dotted notation (e.g., `image.embeddings.completed`), leveraging topic exchange routing. Each event MUST include a unique `event_id` to support idempotency in message processing.

### III. Testing Discipline
Testing efforts MUST prioritize integration tests for core functionality, critical paths, and identified edge cases over exhaustive unit tests. All microservices MUST adopt a standardized test directory structure within their `tests/` folder, with integration tests MAY be organized under logical subdirectories (e.g., `auth/`, `api/`, `core/`, `llm/`) for better organization by domain or feature. Integration test modules MUST follow the naming convention `test_<feature>.py` within their subdirectories and MUST define `pytestmark = pytest.mark.integration`, exercising real network or service boundaries in the dev stack while minimizing mocks to prevent destructive side effects. Unit tests MUST avoid applying the `integration` marker (optionally using `pytestmark = pytest.mark.unit`) so `pytest -m "not integration"` reliably executes only the unit suite. All test directories (including nested subdirectories) MUST contain empty `__init__.py` files for pytest discovery, with shared fixtures under `tests/fixtures/` and static assets under `tests/data/`. Each service's `pytest.ini` MUST register repository-wide markers (`unit` and `integration`) and SHOULD declare service-specific markers.

All microservices MUST achieve >90% test coverage across both unit and integration tests combined. Coverage MUST be measured using `coverage.py` and MUST include all Python modules in the service's source tree. Test exclusions MUST be explicitly justified in service configuration (e.g., `__init__.py` files, test utilities). Coverage reports MUST be generated after test execution and failing coverage MUST block merges. Tests SHOULD prioritize critical code paths, error handling, and integration boundaries over exhaustive coverage of every line.

When testing, developers MUST `cd` into the specific microservice directory before executing `python -m pytest tests/ -v` to ensure correct `PYTHONPATH` resolution. Tests for each microservice MUST be kept within that service's `tests/` folder, with the root `tests/` directory reserved for a manual smoke test and project-wide integration tests. External dependencies (e.g., Playwright) SHOULD be mocked. Basic smoke tests for API endpoints are mandatory. All tests MUST pass before a task is considered complete.

Tests MUST be developed to be portable across Windows and Linux by:
- Building filesystem state with `tempfile` helpers and cleaning via `shutil.rmtree(..., ignore_errors=True)`; keep files past context managers by setting `delete=False` on `NamedTemporaryFile`.
- Using `pathlib.Path` (plus `.resolve()`) for path math and `os.path.join()` only when required by dependencies; convert to strings right before external calls.
- Isolating environment-dependent behavior with fixtures like `patch.dict(os.environ, {...})`, so no test relies on host env vars or absolute paths outside its temp root.
- Initializing services through factories that stub global configuration (e.g., `patch _initialize_platform_crawlers`) and inject the temp directories before any code touches default `/app/...` locations.
- Letting `pytest` drive the event loop by reusing the shared `event_loop` fixture and avoiding ad-hoc loops that diverge between OSes.
- Ensuring imports resolve consistently by appending the repo root (from `Path(__file__).resolve().parents[...]`) once, rather than using raw relative `sys.path` tweaks.

### IV. Development Environment & Configuration
The development environment MUST be initiated using `./up-dev.ps1` (Windows) or `docker compose -f infra/pvm/docker-compose.dev.yml up -d --build`. Database migrations MUST be run via `./migrate.ps1` and optional seeding with `./seed.ps1`. Shared environment variables (e.g., database credentials, common ports) MUST be managed in a common `.env` file, with service-specific overrides in `services/<service_name>/.env`. Shared libraries (`libs/`) MUST be volume-mounted for live development updates. Container rebuilds SHOULD be avoided; use `docker compose down` followed by `docker compose up` for service restarts. Logs MUST be monitored using `docker compose logs -f`.

### V. Data Flow Enforcement
The system's data processing MUST strictly adhere to the defined pipeline: job creation → collection → segmentation → embedding/keypoints → matching → evidence generation → results. `pgvector` MUST be used for efficient storage and similarity search of embeddings. `RabbitMQ` MUST be the sole mechanism for asynchronous event-driven communication between microservices.

### VI. Unified Logging Standard
All microservices MUST implement unified logging using Python's standard `logging` module with the `ContextLogger` wrapper from `common_py.logging_config`. Logger names MUST follow the `service:file` pattern (e.g., `main-api:main`) and use structured logging with keyword arguments instead of string formatting. Each service MUST support correlation ID tracking for request tracing across services, with automatic extraction from RabbitMQ events. Log configuration MUST be environment-based, supporting `LOG_LEVEL` and `LOG_FORMAT` variables. Error logging MUST include exception details and structured context data. The `JsonFormatter` MUST be used for JSON format logs, ensuring all logs include standard fields: `timestamp`, `name`, `level`, `message`, `correlation_id`, and extra structured data.


### VII. Quality Assurance
All microservices MUST pass autopep8 formatting, flake8 linting, all unit tests, and >90% test coverage before any code can be committed or merged. Code MUST be auto-formatted using `autopep8 --in-place --recursive .` from the microservice directory before running flake8 checks to automatically correct style violations. The flake8 configuration MUST include at least E (errors), W (warnings), and F (pyflakes) rulesets to catch syntax errors, style violations, and programming errors. Unit tests MUST be run after every code change using `python -m pytest -m unit` from the microservice directory. Coverage MUST be measured using `coverage.py` with the >90% threshold enforced via pre-commit hooks or CI gates. NO code can be merged if either autopep8 formatting fails, flake8 fails, any unit test fails, or coverage falls below 90%. External dependencies in unit tests SHOULD be mocked to ensure deterministic execution. Development workflows MUST include pre-commit hooks for autopep8, flake8, unit test validation, and coverage checks to catch violations early.

### VIII. Python Version Pinning
Python environments MUST be pinned to version 3.10.8 to ensure consistent development and deployment across all services.

## Architectural Guidelines

*   **Event-Driven Microservices:** The system is built on an event-driven microservices architecture, utilizing RabbitMQ as the message broker for asynchronous communication.
*   **Python-Centric:** Python is the primary language for all microservices and shared libraries.
*   **PostgreSQL with pgvector:** PostgreSQL with the `pgvector` extension is the mandated database for all persistent data, especially for vector similarity search.
*   **Containerization:** Docker and Docker Compose are the standard for local development and deployment packaging.
*   **Image-First Matching:** The core matching logic employs an image-first approach, combining deep learning embeddings (CLIP) with traditional computer vision techniques (AKAZE/SIFT + RANSAC).

## Development Practices

*   **Code Style:** Adherence to PEP 8 guidelines for all Python code.
*   **Type Hinting:** Type hints are strongly encouraged for improved code clarity and maintainability.
*   **Docstrings:** Public APIs and complex functions MUST include comprehensive docstrings.
*   **Structured Logging:** Structured logging MUST be implemented across all services for effective monitoring and debugging.
*   **Shared Libraries:** Common functionalities are encapsulated in shared libraries (`contracts`, `common-py`, `vision-common`) located in `libs/`.
*   **Docker Build Optimization:** `.dockerignore` and optimized Dockerfiles are used to minimize build times and leverage caching.

## Governance

*   **Amendment Procedure:** Amendments to this Constitution MUST be proposed via a pull request, reviewed by at least two core contributors, and approved by the project lead.
*   **Versioning Policy:** This Constitution follows semantic versioning (MAJOR.MINOR.PATCH).
    *   MAJOR: Backward incompatible governance/principle removals or redefinitions.
    *   MINOR: New principle/section added or materially expanded guidance.
    *   PATCH: Clarifications, wording, typo fixes, non-semantic refinements.
*   **Compliance Review:** All code changes and architectural decisions MUST be reviewed for compliance with these principles. Non-compliance MUST be justified and approved by the project lead.
*   **Guidance:** The `RUN.md` document provides runtime development guidance and MUST be consulted for day-to-day operations.

**Version**: 1.7.1 | **Ratified**: TODO(RATIFICATION_DATE): Original adoption date unknown | **Last Amended**: 2025-10-06