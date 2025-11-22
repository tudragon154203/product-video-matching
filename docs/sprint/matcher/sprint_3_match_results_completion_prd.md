# PRD – Match Request Completion Event Rename (Sprint 3)

> Version: 1.0 (repo-synced)  
> Owner: Matcher / Evidence Builder  
> Scope: Contract rename + completion signal behavior

## 1) Overview & Problem
The matching phase currently signals completion with `matchings.process.completed`. To align contracts with topic naming and remove ambiguity, the schema and topic should be renamed to `match.request.completed`. This completion signal must always be emitted once per job—whether zero, few, or many matches are produced—so the evidence builder can finalize (including the zero-match path) and main-api can advance phases without stalling.

## 2) Goals (Must-haves)
- Rename the completion schema to `match_request_completed.json` and use topic `match.request.completed`.
- Emit exactly one `match.request.completed` per job, even when zero matches or many matches are found.
- Update producers (matcher) and consumers (evidence-builder, main-api) to publish/subscribe with the new topic and schema validation.
- Keep contracts/docs/tests in sync with the new name and behavior, including zero-match coverage.

### Non-Goals
- Changing scoring logic, thresholds, or retrieval strategy.
- Altering match.result payloads or evidence generation rules beyond consuming the renamed completion signal.

## 3) Users & Dependencies
- **Main API**: waits on `match.request.completed` to transition to evidence.
- **Evidence Builder**: consumes `match.result` (per pair) plus `match.request.completed` to know when to finish, including zero-match jobs.
- **Client/Results API**: relies on downstream completion to surface job status.

## 4) Functional Requirements
- **Contract**: `libs/contracts/contracts/schemas/match_request_completed.json` with required `{ job_id, event_id }`; description clarifies emission on zero matches.
- **Publisher (Matcher)**:
  - Publishes `match.request.completed` once per `match.request`, regardless of how many `match.result` events were emitted (including none).
  - Uses request `event_id` for the completion event.
- **Consumers**:
  - **Evidence Builder** subscribes to `match.request.completed` and, when `match_count == 0`, immediately publishes `evidences.generation.completed`; otherwise, waits for per-match evidence to finish.
  - **Main API** listens for `match.request.completed` to promote jobs into the evidence phase.
- **Validation**: Update schema references and `@validate_event` usages to the new schema name; aliases continue to support dotted form.
- **Observability/Testing**: Integration tests cover (a) happy path with matches and (b) zero-match path still receiving `match.request.completed`.

## 5) Acceptance Criteria
- The repository contains `match_request_completed.json`; no references to `matchings_process_completed.json` remain.
- Matcher publishes `match.request.completed` for every processed job, including when zero matches are accepted.
- Evidence Builder and Main API subscribe/transition on `match.request.completed` without errors.
- Tests/documentation reflect the renamed contract and zero-match behavior.

## 6) Rollout & Risks
- Deploy matcher/evidence-builder/main-api together to avoid mixed topic names.
- Monitor broker topics for duplicate completion events; ensure idempotency via `event_id`.
- Backward compatibility is not required; legacy topic can be removed after this sprint.

## 7) Open Questions
- Should we include optional counts (`total_matches`) in the completion event for telemetry? (Not required for this sprint.)
