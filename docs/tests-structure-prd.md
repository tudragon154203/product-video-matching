# PRD: Standardized `tests/` Directory for Microservices

## Background
Microservice codebases in the product video matching platform organize their test suites inconsistently. Some services split unit, integration, and contract tests unpredictably, while others mix fixtures and helper scripts alongside test modules. This inconsistency makes it difficult for engineers to understand how to run or extend tests when moving between services.

Establishing a common structure for each service's `tests/` directory will reduce onboarding time, clarify expectations for new test files, and let tooling (documentation, CI jobs, IDE tasks) rely on a predictable layout.

## Goals
- Provide a canonical directory outline for every microservice `tests/` folder.
- Clarify the purpose of each subdirectory so contributors know where to add new files.
- Support pytest configuration and shared fixtures without duplicating effort across services.

## Non-Goals
- Dictate specific test cases or coverage thresholds for services.
- Define repository-wide integration or end-to-end test execution; focus is on per-service layout.
- Prescribe implementation details for individual tests or fixtures.

## User Stories
1. **Service maintainer**: As a maintainer starting a new microservice, I want a ready-made `tests/` layout so I can scaffold the suite consistently.
2. **Feature contributor**: As an engineer adding functionality to an existing service, I want to know exactly where to put unit and integration tests for the change.
3. **QA engineer**: As QA, I want to locate contract tests quickly to confirm schema expectations before a release.

## Requirements
### Functional Requirements
1. Every microservice repository MUST adopt the directory outline listed below within its `tests/` folder.
2. Each subdirectory MUST contain a `README.md` or introductory documentation when domain-specific explanations are necessary.
3. Shared fixtures that apply across test types MUST live under `tests/fixtures/` to encourage reuse.
4. Static assets used by tests MUST be stored under `tests/data/` to keep the working tree organized.

### Non-Functional Requirements
1. The layout MUST support pytest discovery rules (`test_*.py` and `*_test.py`).
2. The structure SHOULD remain lightweight to avoid discouraging small services from adopting it.
3. Documentation SHOULD be updated when new folders are introduced or repurposed.

## Final Directory Structure
All microservices MUST organize their test suite to match the following outline:

```
tests/
├── README.md
├── conftest.py
├── fixtures/
│   ├── __init__.py
│   ├── factories.py
│   ├── payloads.py
│   └── settings.py
├── data/
├── unit/
│   ├── handlers/
│   ├── services/
│   ├── utils/
│   └── domain/
├── integration/
│   ├── api/
│   ├── workflows/
│   ├── messaging/
│   └── external/
└── contract/
    ├── events/
    └── http/
```

## Success Metrics
- 100% of microservices replicate the structure above within one sprint of adoption.
- Contributors report (via retrospective or survey) reduced time to find appropriate test folders.
- CI pipelines leverage the standardized paths for selective test execution without per-service customizations.

## Rollout Plan
1. Publish this PRD and share it with service owners.
2. Update onboarding documentation to reference the standardized layout.
3. Schedule refactoring work for each service to migrate existing tests into the new structure.
4. Monitor adherence during code reviews and flag deviations for follow-up.

## Risks & Mitigations
- **Legacy debt**: Existing services may require non-trivial refactors. Mitigate by planning incremental moves and providing migration scripts.
- **Over-prescription**: Teams might have unique needs. Mitigate by allowing deeper nesting within `unit/` or `integration/` while keeping top-level folders consistent.
- **Knowledge gaps**: Engineers may be unaware of the change. Mitigate with brown-bag sessions and documentation updates.

## Open Questions
- Do any services require additional subfolders (e.g., performance tests) that should be standardized later?
- Should we provide cookiecutter or template scripts to bootstrap the directory layout automatically?

