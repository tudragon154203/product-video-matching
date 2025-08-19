# Progress

## August 2025 Updates
- Completed import verification across all microservices after refactoring
- Fixed syntax errors in vision-keypoint service
- Resolved import issues in evidence-builder service
- Added vision-common library to Dockerfiles for vision services
- Refactored product-segmentor to use vision-common:
  - Replaced custom progress tracking with JobProgressManager
  - Implemented WatermarkTimerManager
  - Added CompletionEventPublisher
  - Removed redundant custom code (~200 lines)
- Improved consistency across vision services

## Completed
- Sprint 1: Defined microservice specs and the end-to-end video→product matching pipeline boundaries
- Sprint 2: Unified Main API spec and added LLM (Ollama) query normalization/fallback path
- Sprint 3: Revamped contracts and schemas; established stricter validation and versioning plan
- Sprint 4: Added Gemini fallback support in Main API to harden LLM pathways
- Sprint 5: Renamed services for clarity (catalog collector → dropship-product-finder, media ingestion → video-crawler)
- Sprint 6.0: Produced end-to-end data-flow ASCII diagram and validated phase ordering
- Sprint 6.1: Debug and stabilization across services during integration
- Sprint 6.2a: Introduced multiple-events pattern to improve batching and throughput
- Sprint 6.2b: Added videos batch pre-announce to reduce tail latency and coordinate consumers
- Sprint 7: Addressed zero/edge-case handling in the pipeline and contracts
- Sprint 8: Designed Product-Segmentor and adjusted event flow to improve matching precision
- 2025-08-18: Reversed LLM order in main-api (Gemini first)
- 2025-08-18: Added rule requiring automatic Memory Bank updates after tasks
- 2025-08-18: Removed published_at column from database schema and YouTube crawler

## Pending
- Sprint 9 (in progress): Retire dedicated vector-index service
  - Migrate matcher to consume embeddings directly from storage/DB
  - Remove/deprecate vector-index events and update dependent services
  - Make Qdrant optional/off by default in dev compose
  - Strengthen integration tests and performance checks post-removal
  - Update docs (RUN.md, contracts notes) and clean dead code paths