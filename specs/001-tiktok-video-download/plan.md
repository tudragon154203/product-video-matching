
# Implementation Plan: TikTok Video Download & Keyframe Extraction

**Branch**: `001-tiktok-video-download` | **Date**: 2025-09-30 | **Spec**: [TikTok Video Download & Keyframe Extraction Integration in video-crawler](spec.md)
**Input**: Feature specification from `O:\\product-video-matching\\tiktok-video-download\\specs\\001-tiktok-video-download\\spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Extend the video-crawler service to download TikTok videos using yt-dlp from webViewUrl, extract keyframes using the existing length_adaptive_extractor, and persist keyframe metadata to the database, following the same job/phase/event-driven model used for YouTube integration.

## Technical Context
**Language/Version**: Python 3.10.8 (as per constitution)
**Primary Dependencies**: yt-dlp, existing keyframe_extractors module (specifically length_adaptive_extractor.py in services/video-crawler/utils/), video_frame_crud from libs/common-py  
**Storage**: PostgreSQL with pgvector for metadata, local filesystem using DATA_ROOT_CONTAINER for video/keyframe storage following the YouTube implementation pattern  
**Testing**: pytest for unit and integration tests  
**Target Platform**: Linux server (Docker container)  
**Project Type**: single - extending existing video-crawler service  
**Performance Goals**: Extract max 20 keyframes per video (configurable), with resilience to handle extraction failures  
**Constraints**: Maximum 500MB file size limit, retry up to 3 times with exponential backoff on network failures, basic file validation (exists, non-zero size)  
**Scale/Scope**: Integration with existing TikTok crawler, reuse job/phase/event-driven model from YouTube integration

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Microservice Structure**: Adherence to standardized microservice layout. (Extending existing video-crawler service with proper structure: app/main.py, handlers/, services/, config_loader.py)
- [x] **II. Event Contracts**: All inter-service communication conforms to defined event contracts. (No new event contracts required for this feature)
- [x] **III. Testing Discipline**: Prioritization of integration tests, standardized test structure, pytest markers, and test execution. (Will follow standard testing approach with integration and unit tests)
- [x] **IV. Development Environment & Configuration**: Correct environment setup, configuration management, and efficient development practices. (Will use existing dev environment with Docker and docker-compose)
- [x] **V. Data Flow Enforcement**: Strict adherence to the defined data processing pipeline and technology usage. (Following pipeline: job creation → collection → segmentation → embedding/keypoints → matching, using pgvector and RabbitMQ)
- [x] **VI. Unified Logging Standard**: Implementation of structured logging with ContextLogger, correlation ID tracking, and environment-based configuration. (Will implement unified logging as per constitution)
- [x] **VII. Quality Assurance**: flake8 linting passes and all unit tests pass before code commits and merges. (Will ensure code passes flake8 and all tests before merge)
- [x] **VIII. Python Version Pinning**: Python environments pinned to version 3.10.8. (Using Python 3.10.8 as required)

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
│   ├── api/
│   ├── auth/
│   ├── core/
│   └── llm/
└── unit/

# Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure]
```

**Structure Decision**: Option 1 - Single project (DEFAULT) since this extends the existing video-crawler service rather than creating a new web or mobile app

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task (none remain after clarifications)
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice (yt-dlp, keyframe extraction, video_frame_crud):
     Task: "Find best practices for {tech} in TikTok video download and keyframe extraction context"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType gemini`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each contract → contract test task [P]
- Each entity → model creation task [P] 
- Each user story → integration test task
- Implementation tasks to make tests pass

**Ordering Strategy**:
- TDD order: Tests before implementation 
- Dependency order: Models before services before UI
- Mark [P] for parallel execution (independent files)

**Estimated Output**: 25-30 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---
*Based on Constitution v1.5.0 - See `/memory/constitution.md`*
