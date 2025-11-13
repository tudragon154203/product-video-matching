# Tasks: Implement Matcher Microservice

**Input**: Design documents from `O:\product-video-matching\implement-matcher\specs\002-implement-matcher-microservice\`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → If not found: ERROR "No implementation plan found"
   → Extract: tech stack, libraries, structure
2. Load optional design documents:
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup tasks
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: contract tests, integration tests
   → Core: models, services, CLI commands
   → Integration: DB, middleware, logging
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → All contracts have tests?
   → All entities have models?
   → All endpoints implemented?
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

## Phase 3.1: Setup
- [X] T001 Create `services/matcher` directory and basic files (`main.py`, `config_loader.py`, `Dockerfile`, `requirements.txt`, `pytest.ini`, `.flake8`).
- [X] T002 Add `matcher` service to `infra/pvm/docker-compose.dev.yml`.
- [X] T003 [P] Configure linting (`.flake8`) and formatting tools for `services/matcher`.
- [X] T004 Pin Python version to 3.10.8 in `services/matcher/Dockerfile` and `requirements.txt`.

## Phase 3.2: Quality and Tests Setup ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: Quality gates MUST be configured and tests MUST FAIL before ANY implementation**
- [X] T005 [P] Install `flake8` with E, W, F rulesets in `services/matcher/requirements.txt`.
- [X] T006 [P] Configure `pytest` for strict markers and unit/integration separation in `services/matcher/pytest.ini`.
- [X] T007 [P] Contract test `matcher_input.json` in `services/matcher/tests/contract/test_matcher_input.py`.
- [X] T008 [P] Contract test `matcher_output.json` in `services/matcher/tests/contract/test_matcher_output.py`.
- [X] T009 [P] Integration test "Successful Match" scenario in `services/matcher/tests/integration/test_successful_match.py`.
- [X] T010 [P] Integration test "No Match Found" scenario in `services/matcher/tests/integration/test_no_match.py`.
- [X] T011 [P] Integration test "Poor Quality Product Image" edge case in `services/matcher/tests/integration/test_poor_quality_image.py`.
- [X] T012 [P] Integration test "Multiple Products in a Single Frame" edge case in `services/matcher/tests/integration/test_multiple_products.py`.
- [X] T013 [P] Integration test "Unrecoverable Error During Matching" edge case in `services/matcher/tests/integration/test_unrecoverable_error.py`.
- [X] T014 Validate `flake8` passes with `services/matcher` codebase.
- [X] T015 Validate `python -m pytest -m unit` passes for `services/matcher`.

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [X] T016 [P] Define `Product` data model in `services/matcher/services/data_models.py`.
- [X] T017 [P] Define `VideoFrame` data model in `services/matcher/services/data_models.py`.
- [X] T018 [P] Define `MatchResult` data model in `services/matcher/services/data_models.py`.
- [X] T019 Implement core matching logic (CLIP embeddings and AKAZE/SIFT + RANSAC) in `services/matcher/services/matcher_service.py`.
- [X] T020 Create RabbitMQ event handler for matching requests in `services/matcher/handlers/match_request_handler.py`.

## Phase 3.4: Integration
- [X] T021 Integrate with RabbitMQ for consuming matching requests in `services/matcher/main.py`.
- [X] T022 Integrate with RabbitMQ for publishing matching results in `services/matcher/handlers/match_request_handler.py`.
- [X] T023 Implement structured logging using `common_py.logging_config` in `services/matcher/main.py` and `handlers/match_request_handler.py`.

## Phase 3.5: Polish
- [X] T024 [P] Add unit tests for core matching logic in `services/matcher/tests/unit/test_matcher_service.py`.
- [X] T025 Optimize performance for high volume matching requests in `services/matcher/services/matcher_service.py`.
- [X] T026 [P] Update `services/matcher/README.md`.

## Dependencies
- Setup tasks (T001-T004) before Quality and Tests Setup (T005-T015).
- Quality and Tests Setup (T005-T015) before Core Implementation (T016-T020).
- Core Implementation (T016-T020) before Integration (T021-T023).
- Integration (T021-T023) before Polish (T024-T026).
- T016, T017, T018 (data models) before T019 (matching logic).
- T019 (matching logic) before T020 (event handler).
- T020 (event handler) before T022 (publishing results).
- T021 (consuming requests) before T020 (event handler).
- T023 (logging) can be done in parallel with other tasks in Integration phase.

## Parallel Example
```
# Launch T003-T004 together for initial setup:
Task: "Configure linting (.flake8) and formatting tools for services/matcher"
Task: "Pin Python version to 3.10.8 in services/matcher/Dockerfile and requirements.txt"

# Launch T005-T006 together for quality setup:
Task: "Install flake8 with E, W, F rulesets in services/matcher/requirements.txt"
Task: "Configure pytest for strict markers and unit/integration separation in services/matcher/pytest.ini"

# Launch T007-T013 together for contract and integration tests:
Task: "Contract test matcher_input.json in services/matcher/tests/contract/test_matcher_input.py"
Task: "Contract test matcher_output.json in services/matcher/tests/contract/test_matcher_output.py"
Task: "Integration test \"Successful Match\" scenario in services/matcher/tests/integration/test_successful_match.py"
Task: "Integration test \"No Match Found\" scenario in services/matcher/tests/integration/test_no_match.py"
Task: "Integration test \"Poor Quality Product Image\" edge case in services/matcher/tests/integration/test_poor_quality_image.py"
Task: "Integration test \"Multiple Products in a Single Frame\" edge case in services/matcher/tests/integration/test_multiple_products.py"
Task: "Integration test \"Unrecoverable Error During Matching\" edge case in services/matcher/tests/integration/test_unrecoverable_error.py"

# Launch T016-T018 together for data model definitions:
Task: "Define Product data model in services/matcher/services/data_models.py"
Task: "Define VideoFrame data model in services/matcher/services/data_models.py"
Task: "Define MatchResult data model in services/matcher/services/data_models.py"

# Launch T024 and T026 together for polish tasks:
Task: "Add unit tests for core matching logic in services/matcher/tests/unit/test_matcher_service.py"
Task: "Update services/matcher/README.md"
```

## Notes
- [P] tasks = different files, no dependencies
- Verify tests fail before implementing
- Commit after each task
- Avoid: vague tasks, same file conflicts

## Task Generation Rules
*Applied during main() execution*

1. **From Contracts**:
   - Each contract file → contract test task [P]
   - Each endpoint → implementation task
   
2. **From Data Model**:
   - Each entity → model creation task [P]
   - Relationships → service layer tasks
   
3. **From User Stories**:
   - Each story → integration test [P]
   - Quickstart scenarios → validation tasks

4. **Ordering**:
   - Setup → Tests → Models → Services → Endpoints → Polish
   - Dependencies block parallel execution

## Validation Checklist
*GATE: Checked by main() before returning*

- [X] All contracts have corresponding tests
- [X] All entities have model tasks
- [X] All tests come before implementation
- [X] Parallel tasks truly independent
- [X] Each task specifies exact file path
- [X] No task modifies same file as another [P] task
