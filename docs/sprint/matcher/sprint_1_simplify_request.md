# Sprint 1 - Simplify Match Request Payload

## Summary
- Collapse `match_request` contract to a minimal envelope so downstream services derive context from persisted job configuration.
- Keep `job_id` as the only business identifier in the payload and introduce an `event_id` to guarantee idempotent processing.
- Update the matcher workflow, contracts, and observability to align with the simplified request surface.

## Background
The current `libs/contracts/contracts/schemas/match_request.json` schema requires clients to provide `industry`, `product_set_id`, `video_set_id`, and `top_k` along with `job_id`. Those values already live in `main-api` and the job manifest stored in Postgres. Duplicating them in the request causes drift when jobs are edited and makes retried events brittle because the extra fields must stay in sync with the authoritative job record.

## Problem Statement
1. Repeated metadata in the match request inflates payload size and creates opportunities for mismatched parameters across retries or consumers.
2. Retry and deduplication logic is limited to `job_id`, which is not sufficient for idempotency when multiple match requests fire for the same job.
3. The additional fields make mocks, fixtures, and documentation harder to maintain, slowing experiments in the matcher domain.

## Goals
- Reduce the match request payload to the minimal required fields for orchestrating a match run.
- Provide an explicit idempotency key so the matcher can detect duplicate deliveries.
- Document contract changes and rollout expectations for platform, data, and service owners.

## Non-Goals
- Changing the structure of match result payloads.
- Refactoring how jobs are created or stored in `main-api`.
- Introducing new transport guarantees beyond documenting how to use `event_id`.

## Proposed Solution
### Contract Changes
- Update `libs/contracts/contracts/schemas/match_request.json`:
  - Properties: `job_id` (string, required), `event_id` (string, required, format `uuid`).
  - Remove requirements for `industry`, `product_set_id`, `video_set_id`, and `top_k`.
  - Set `additionalProperties` to `false` to defend the slimmer contract.
- Regenerate any typed clients or code that ingest the schema (see `libs/common-py` consumers).

### Event Flow
- `main-api` publishes match requests containing `event_id` generated per dispatch attempt (`uuid4`).
- Consumers (`matcher`, `results-api` background syncs) treat `event_id` as the primary idempotency key, storing it alongside existing job execution logs.
- Retries reuse the same `event_id` when replaying the event to keep processing idempotent.

### Service Workstream
- **main-api**: Source `job_id` from persisted job, enrich payload with new `event_id`, remove redundant fields, update tests/fixtures.
- **matcher**: Adjust request deserialization, replace existing metadata lookups with DB fetch by `job_id`, implement idempotent guard using `event_id`.
- **results-api**: Ensure any webhook or polling flows that rely on the legacy fields now fetch metadata via internal APIs.
- **Data/Analytics**: Update ingestion logic to capture `event_id` for traceability.

### Observability & Tooling
- Add structured log fields (`event_id`, `job_id`) in matcher runs.
- Update dashboards and alerts to pivot on `event_id` for duplicate detection metrics.
- Revise QA fixtures in `tests/` to the new payload contract.

## Acceptance Criteria
- `match_request` schema validates only `job_id` and `event_id`, both required, with `event_id` marked as a UUID string and `additionalProperties` disabled.
- All producers and consumers compile and their unit/integration tests pass with the updated contract.
- Observability dashboards display `event_id` for match executions.
- Documentation updated (this PRD + API/CONTRACTS references) before rollout sign-off.

## Rollout Plan
1. Land schema update and contract regeneration in a feature branch.
2. Coordinate with service owners to update code paths consuming the contract.
3. Deploy to staging with matcher + main-api behind feature flag reading the new payload.
4. Run regression tests and smoke suite; verify idempotent retry scenario using duplicated `event_id`.
5. Promote to production during scheduled deployment window once validation passes.

## Risks & Mitigations
- **Consumer drift**: Some downstream consumer may still expect legacy fields. Mitigation: contract release notes, schema version bump, temporary compatibility shim via validation toggle in staging.
- **Idempotency misuse**: Producers might generate a fresh `event_id` on retries. Mitigation: document expectation in runbook, add alert when duplicates appear with different `event_id`.
- **Breaking tests**: Shared fixtures must be updated simultaneously; coordinate with QA to update `tests/conftest.py` helpers in the same sprint.

## Open Questions
- Should we enforce UUID format or allow any opaque string for `event_id`? (Default recommendation: `format: uuid`.)
- Do we need to persist `event_id` in the job execution table for historical analytics, or is transient logging sufficient?
- Are there external clients emitting match requests directly who need migration support?

## Appendix
- Current schema: `libs/contracts/contracts/schemas/match_request.json` (v before change).
- Related schemas for reference: `libs/contracts/contracts/schemas/match_result.json`, `libs/contracts/contracts/schemas/match_request_completed.json`.
- For implementation tasks, see Jira epic MATCHER-102.
