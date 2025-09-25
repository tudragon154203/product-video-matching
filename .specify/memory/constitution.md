<!--
Sync Impact Report:
- Version change: 0.0.0 (assumed) → 1.0.0
- List of modified principles: All 5 existing principles replaced with 5 new, consolidated principles.
- Added sections: None.
- Removed sections: None.
- Templates requiring updates:
    - .specify/templates/plan-template.md: ✅ updated
    - .specify/templates/spec-template.md: ⚠ pending (no explicit changes, but implicit alignment)
    - .specify/templates/tasks-template.md: ⚠ pending (no explicit changes, but implicit alignment)
    - .specify/templates/commands/*.md: ✅ updated (no changes to the command files themselves, but the constitution output will be generic)
    - README.md: ✅ updated (no changes needed, already aligned)
    - RUN.md: ✅ updated (no changes needed, already aligned)
- Follow-up TODOs: TODO(RATIFICATION_DATE): Original adoption date unknown
-->
# Product-Video Matching System Constitution

## Core Principles

### I. Microservice Structure
All microservices MUST adhere to a standardized structure: `app/main.py` (entry point), `handlers/` (RabbitMQ event handlers), `services/` (business logic), `config_loader.py` (environment configuration), `Dockerfile`, and a service-specific `.env` file. This ensures consistency, maintainability, and ease of onboarding for new developers.

### II. Event Contracts
All inter-service communication via RabbitMQ MUST conform to defined event contracts. Events in `libs/contracts/contracts/schemas/` MUST utilize JSON schema validation. Routing keys MUST follow a dotted notation (e.g., `image.embeddings.completed`), leveraging topic exchange routing. Each event MUST include a unique `event_id` to support idempotency in message processing.

### III. Testing Discipline
Testing efforts MUST prioritize integration tests for core functionality, critical paths, and identified edge cases. Exhaustive unit tests are to be avoided in favor of broader integration coverage. When testing, developers MUST `cd` into the specific microservice directory before executing `python -m pytest tests/ -v` to ensure correct `PYTHONPATH` resolution. External dependencies (e.g., Playwright) SHOULD be mocked. Basic smoke tests for API endpoints are mandatory. All tests MUST pass before a task is considered complete.

### IV. Development Environment & Configuration
The development environment MUST be initiated using `./up-dev.ps1` (Windows) or `docker compose -f infra/pvm/docker-compose.dev.yml up -d --build`. Database migrations MUST be run via `./migrate.ps1` and optional seeding with `./seed.ps1`. Shared environment variables (e.g., database credentials, common ports) MUST be managed in a common `.env` file, with service-specific overrides in `services/<service_name>/.env`. Shared libraries (`libs/`) MUST be volume-mounted for live development updates. Container rebuilds SHOULD be avoided; use `docker compose down` followed by `docker compose up` for service restarts. Logs MUST be monitored using `docker compose logs -f`.

### V. Data Flow Enforcement
The system's data processing MUST strictly adhere to the defined pipeline: job creation → collection → segmentation → embedding/keypoints → matching → evidence generation → results. `pgvector` MUST be used for efficient storage and similarity search of embeddings. `RabbitMQ` MUST be the sole mechanism for asynchronous event-driven communication between microservices.

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

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): Original adoption date unknown | **Last Amended**: 2025-09-25
