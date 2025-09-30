# Tasks: TikTok Video Download & Keyframe Extraction

**Input**: Design documents from `/specs/001-tiktok-video-download/`
**Prerequisites**: plan.md (required), research.md, data-model.md, quickstart.md

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
- [ ] T001 Create TikTokDownloader wrapper service in services/video-crawler/platform_crawler/tiktok/tiktok_downloader.py
- [ ] T002 Add yt-dlp dependency to services/video-crawler/requirements.txt
- [ ] T003 [P] Update config to support TikTok video and keyframe storage paths
- [ ] T004 Pin Python version to 3.10.8 in Dockerfile

## Phase 3.2: Quality and Tests Setup ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: Quality gates MUST be configured and tests MUST FAIL before ANY implementation**
- [ ] T005 [P] Install flake8 with E, W, F rulesets in services/video-crawler/requirements-test.txt
- [ ] T006 [P] Configure pytest for strict markers and unit/integration separation in services/video-crawler/pytest.ini
- [ ] T007 [P] Configure pre-commit hooks for flake8 and unit test validation in services/video-crawler/.pre-commit-config.yaml
- [ ] T008 [P] Integration test for TikTok video download in services/video-crawler/tests/integration/tiktok/test_tiktok_download.py
- [ ] T009 [P] Integration test for keyframe extraction in services/video-crawler/tests/integration/tiktok/test_keyframe_extraction.py
- [ ] T010 [P] Unit test for TikTokDownloader in services/video-crawler/tests/unit/tiktok/test_tiktok_downloader.py
- [ ] T011 [P] Unit test for TikTok keyframe functionality in services/video-crawler/tests/unit/tiktok/test_tiktok_keyframes.py
- [ ] T012 Validate flake8 passes with video-crawler service codebase
- [ ] T013 Validate `python -m pytest -m unit` passes (all green state)

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T014 [P] TikTok Video model extension in services/video-crawler/models/video.py
- [ ] T015 [P] TikTokDownloader class implementation in services/video-crawler/platform_crawler/tiktok/tiktok_downloader.py
- [ ] T016 [P] Update Video model to include download_url, local_path, has_download, and keyframes fields
- [ ] T017 Implement download functionality with 500MB file size limit
- [ ] T018 Implement retry logic with exponential backoff for network failures
- [ ] T019 Implement basic file validation (exists, non-zero size)
- [ ] T020 Integrate with existing length_adaptive_extractor for keyframe extraction
- [ ] T021 Store extracted keyframes in DATA_ROOT_CONTAINER/keyframes/tiktok/{video_id}/
- [ ] T022 Store downloaded videos in DATA_ROOT_CONTAINER/videos/tiktok/
- [ ] T023 Persist keyframe metadata to database using video_frame_crud

## Phase 3.4: Integration
- [ ] T024 Connect TikTokDownloader to video storage configuration
- [ ] T025 Integrate with video_frame_crud for metadata persistence
- [ ] T026 Implement error handling for TikTok anti-bot measures
- [ ] T027 Add logging using ContextLogger as per constitution

## Phase 3.5: Polish
- [ ] T028 [P] Unit tests for download logic in services/video-crawler/tests/unit/tiktok/test_download_logic.py
- [ ] T029 [P] Unit tests for error handling in services/video-crawler/tests/unit/tiktok/test_error_handling.py
- [ ] T030 Performance tests for video download and keyframe extraction
- [ ] T031 [P] Update documentation for TikTok integration
- [ ] T032 Implement cleanup logic for video files after 7 days (keyframe files kept permanently)
- [ ] T033 Run manual validation with test video: https://www.tiktok.com/@lanxinx/video/7548644205690670337

## Dependencies
- Quality setup (T005-T007) before any tests (T008-T011)
- Quality validation (T012-T013) after tests but before implementation
- Tests (T008-T011) before implementation (T014-T023)
- T014 blocks T016, T22, T23
- T015 blocks T017, T18, T19
- T020 blocks T21
- T022 blocks T21, T23
- T023 blocks T32
- T032 blocks T33
- Implementation before polish (T028-T033)

## Parallel Example
```
# Launch T005-T007 together for quality setup:
Task: "Install flake8 with E, W, F rulesets in services/video-crawler/requirements-test.txt"
Task: "Configure pytest for strict markers and unit/integration separation in services/video-crawler/pytest.ini"
Task: "Configure pre-commit hooks for flake8 and unit test validation in services/video-crawler/.pre-commit-config.yaml"

# Launch T008-T011 together for test creation:
Task: "Integration test for TikTok video download in services/video-crawler/tests/integration/tiktok/test_tiktok_download.py"
Task: "Integration test for keyframe extraction in services/video-crawler/tests/integration/tiktok/test_keyframe_extraction.py"
Task: "Unit test for TikTokDownloader in services/video-crawler/tests/unit/tiktok/test_tiktok_downloader.py"
Task: "Unit test for TikTok keyframe functionality in services/video-crawler/tests/unit/tiktok/test_tiktok_keyframes.py"
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

- [ ] All contracts have corresponding tests
- [ ] All entities have model tasks
- [ ] All tests come before implementation
- [ ] Parallel tasks truly independent
- [ ] Each task specifies exact file path
- [ ] No task modifies same file as another [P] task