# Sprint 11: Unified Logging Standards

## Purpose
- Establish a single, consistent logger initialization pattern across all Python code (excluding the front‑end) to improve log discoverability, filtering, and cross‑service analysis.
- Standardize the logger name format to include both the microservice and the file context.

## Scope
- In scope: all Python modules under `services/*` (except `services/front-end`), all shared Python libraries under `libs/*`, and repository scripts under `scripts/*`.
- Out of scope: front‑end code and tooling; log transport/aggregation infrastructure; log message contents and levels.

## Standard
- Module‑level logger must be declared once per file using: `logger = configure_logging("microservice-name:file-name")`.
- The logger name must follow the exact `microservice:file` structure; no dots, spaces, or additional segments.

## Naming Rules
- microservice-name:
  - Use the service folder name under `services/` (e.g., `main-api`, `results-api`, `video-crawler`, `matcher`, `evidence-builder`, `dropship-product-finder`, `vision-embedding`, `vision-keypoint`, `product-segmentor`).
  - For shared libraries under `libs/`, use the library name (e.g., `common-py`, `vision-common`).
  - For repository utilities under `scripts/`, use `scripts`.
  - Allowed characters: lowercase letters, digits, and hyphens (`[a-z0-9-]+`).
- file-name:
  - Use the Python file’s stem (filename without `.py`) for the module where the logger is defined (e.g., `main`, `cleanup_service`, `vector_searcher`).
  - For `__init__.py`, use the immediate package name (directory name).
  - Allowed characters: lowercase letters, digits, and underscores (`[a-z0-9_]+`).

## Examples (illustrative)
- `main-api:video_endpoints`
- `video-crawler:cleanup_service`
- `matcher:pair_score_calculator`
- `vision-embedding:clip_processor`
- `common-py:messaging`
- `scripts:run_migrations`

## Policy
- This naming supersedes prior guidance that used only the service name or dotted module paths. The new canonical form is `service:file`.
- Each Python module should contain exactly one module‑level logger constructed with the standard pattern.
- Do not introduce alternative or nested logger names (e.g., no `service.submodule`, no `service:file:subpart`).

## Acceptance Criteria
- 100% of Python modules within the scope declare their logger with the exact `configure_logging("microservice-name:file-name")` format.
- No occurrences of `logging.getLogger(__name__)` remain within the scope.
- No occurrences of `configure_logging("..." )` without a colon separating `microservice` and `file` remain within the scope.
- CI validation is defined to flag any logger names that do not match `^[a-z0-9-]+:[a-z0-9_]+$` or modules lacking a compliant declaration.
- Existing log levels, formats (text/json), correlation ID handling, and message contents remain unchanged.

## Migration Guidance
- Replace any non‑compliant logger initializations with the standard form using the correct `microservice-name` and the module’s `file-name`.
- Retain any explicit log level or format configuration parameters that are already in use; only the logger name is standardized in this sprint.
- For packages with many modules, apply the change at module scope per file; do not centralize a single logger across multiple files.

## Observability & Ops Notes
- Dashboards, alerts, and saved searches that filter by logger name must be updated to the new `service:file` identifiers.
- Backend log processing and correlation ID features continue to function as before; this change only affects the logger name field.

## Non‑Goals
- Changing front‑end logging or build tooling for the front‑end.
- Modifying log schemas, transports, sinks, or retention policies.
- Refactoring business logic, error handling, or message text.

## Definition of Done
- All target modules updated and validated against the naming regex `^[a-z0-9-]+:[a-z0-9_]+$`.
- CI includes a check that fails on non‑conforming logger names or missing module‑level declarations in Python files within the scope.
- Observability searches updated to the new `service:file` naming convention where applicable.

