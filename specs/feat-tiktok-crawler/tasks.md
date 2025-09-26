# Tasks: TikTok Platform Crawler

**Input**: Design documents from `/specs/feat-tiktok-crawler/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → Extract: Python 3.11, httpx, sse-starlette, existing microservice patterns
2. Load optional design documents:
   → data-model.md: TikTokVideo entity → model tasks
   → contracts/tiktok-api.yaml: POST /tiktok/search → contract test task
   → research.md: Technical decisions → setup tasks
   → quickstart.md: Test scenarios → integration tests
3. Generate tasks by category:
   → Setup: TikTok crawler directory structure
   → Tests: Contract tests, integration tests
   → Core: TikTok crawler implementation
   → Integration: RabbitMQ event handler updates
   → Polish: Unit tests, error handling
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → Contract has test
   → Entity has model
   → Endpoint implemented
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Microservice**: `services/video-crawler/`
- **Platform crawler**: `services/video-crawler/platform_crawler/tiktok/`
- **Tests**: `services/video-crawler/tests/unit/test_tiktok_crawler.py`

## Phase 3.1: Setup
- [ ] T001 Create TikTok crawler directory structure in services/video-crawler/platform_crawler/tiktok/
- [ ] T002 Add httpx and sse-starlette dependencies to services/video-crawler/requirements.txt
- [ ] T003 [P] Add TIKTOK_API_URL configuration to services/video-crawler/config_loader.py

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [ ] T004 [P] Contract test POST /tiktok/search API in services/video-crawler/tests/contract/test_tiktok_api.py
- [ ] T005 [P] Integration test TikTok crawler in services/video-crawler/tests/integration/test_tiktok_integration.py
- [ ] T006 [P] Test TikTok platform query extraction in services/video-crawler/tests/unit/test_platform_queries.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T007 [P] TikTokVideo model in services/video-crawler/platform_crawler/tiktok/tiktok_models.py
- [ ] T008 [P] TikTokSearcher HTTP client in services/video-crawler/platform_crawler/tiktok/tiktok_searcher.py
- [ ] T009 [P] TikTokCrawler implementation in services/video-crawler/platform_crawler/tiktok/tiktok_crawler.py
- [ ] T010 Update platform crawler initialization in services/video-crawler/services/service.py
- [ ] T011 Update platform query extraction logic in services/video-crawler/services/service.py
- [ ] T012 Add TikTok download directory handling in services/video-crawler/services/service.py

## Phase 3.4: Integration
- [ ] T013 Connect TikTokSearcher to external API with exponential backoff
- [ ] T014 Implement real-time streaming response handling
- [ ] T015 Add TikTok platform to video metadata processing
- [ ] T016 Update error handling for TikTok API failures

## Phase 3.5: Polish
- [ ] T017 [P] Unit tests for TikTok models in services/video-crawler/tests/unit/test_tiktok_models.py
- [ ] T018 [P] Unit tests for TikTok searcher in services/video-crawler/tests/unit/test_tiktok_searcher.py
- [ ] T019 Performance testing with concurrent requests
- [ ] T020 [P] Update API documentation in services/video-crawler/README.md
- [ ] T021 Run quickstart.md validation scenarios
- [ ] T22 Remove any duplication with existing YouTube patterns

## Dependencies
- Tests (T004-T006) before implementation (T007-T012)
- T007 blocks T008, T009
- T008 blocks T013
- T009 blocks T010
- Implementation before integration (T013-T016)
- Integration before polish (T017-T022)

## Parallel Example
```
# Launch T004-T006 together:
Task: "Contract test POST /tiktok/search API in services/video-crawler/tests/contract/test_tiktok_api.py"
Task: "Integration test TikTok crawler in services/video-crawler/tests/integration/test_tiktok_integration.py"
Task: "Test TikTok platform query extraction in services/video-crawler/tests/unit/test_platform_queries.py"

# Launch T007-T009 together:
Task: "TikTokVideo model in services/video-crawler/platform_crawler/tiktok/tiktok_models.py"
Task: "TikTokSearcher HTTP client in services/video-crawler/platform_crawler/tiktok/tiktok_searcher.py"
Task: "TikTokCrawler implementation in services/video-crawler/platform_crawler/tiktok/tiktok_crawler.py"
```

## Notes
- [P] tasks = different files, no dependencies
- Verify tests fail before implementing
- Commit after each task
- Follow existing YouTube crawler patterns
- Use existing RabbitMQ events (no new events)
- No rate limiting implementation

## Task Generation Rules
*Applied during main() execution*

1. **From Contracts**:
   - contracts/tiktok-api.yaml → contract test task [P]
   - POST /tiktok/search endpoint → implementation task

2. **From Data Model**:
   - TikTokVideo entity → model creation task [P]
   - TikTokSearchResponse → service layer tasks

3. **From User Stories**:
   - Quickstart test scenarios → integration tests [P]
   - Error handling scenarios → validation tasks

4. **Ordering**:
   - Setup → Tests → Models → Services → Integration → Polish
   - Dependencies block parallel execution

## Validation Checklist
*GATE: Checked by main() before returning*

- [x] Contract has corresponding test (T004)
- [x] Entity has model task (T007)
- [x] All tests come before implementation
- [x] Parallel tasks truly independent
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] Uses existing RabbitMQ events
- [x] No rate limiting implementation