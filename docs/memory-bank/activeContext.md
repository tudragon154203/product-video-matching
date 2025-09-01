# Active Context

## Current Focus
- Sprint 9: ✅ COMPLETED - Retired the dedicated vector-index service and simplified the matcher to consume embeddings directly from storage/DB. Updated contracts and consumers to stop emitting/consuming vector-index events. Made Qdrant infra optional/off by default in dev.
- Current LLM strategy: Gemini-first with Ollama fallback (implemented in main-api/services/llm_service.py)
- 2025-08-18: Completed removal of published_at column from database schema and YouTube crawler
- 2025-08-19: ✅ COMPLETED - Updated memory bank with current project state and recent sprint completions
- Current focus: eBay integration for dropship-product-finder (30% complete), YouTube crawler implementation for video-crawler service (85% complete), and front-end animation features implementation (100% complete)
- 2025-08-24: ✅ COMPLETED - Implemented job listing feature with GET /api/jobs endpoint in main-api, including pagination, status filtering, and comprehensive test coverage
- 2025-08-22: ✅ COMPLETED - Updated memory bank with current project state and added testing instructions to CLAUDE.md
- 2025-08-22: ✅ COMPLETED - Cleaned up failing unit tests with httpx.AsyncClient mock configuration issues across main-api and dropship-product-finder services
- 2025-08-22: ✅ COMPLETED - Marked eBay browse search minimal code guide as completed in memory bank

## Active Development Areas
- **Dropship Product Finder**: eBay integration implementation (OAuth, Browse API, image processing)
  * eBay Browse API integration
  * Product deduplication by EPID
  * Image processing pipeline
  * Database schema updates
- **Video Crawler**: YouTube search and download functionality using yt-dlp
- **Vision Services**: Consistent use of vision-common library across all vision services
- **Main API**: Job listing and management functionality
  * GET /api/jobs endpoint with pagination (limit/offset)
  * Status filtering (completed, failed, in_progress)
  * Ordering by creation date (newest first)
  * Comprehensive test coverage with edge cases

## Recent Completions
- Sprint 9: Vector-index service retirement and matcher simplification
- Database schema updates (removed published_at column)
- Memory bank automation rule implementation
- Vision services refactoring to use vision-common library
- YouTube crawler core functionality implemented
- Job listing feature implementation with full API specification and test coverage

## Next Steps
- Complete eBay integration phases (OAuth implementation, Browse API integration, image pipeline)
- Implement YouTube crawler with proper search and download functionality
- Strengthen integration tests across the updated pipeline
- Update documentation to reflect current architecture and capabilities
- Monitor performance after vector-index service removal
- Complete eBay integration missing components
- Finalize YouTube crawler testing
- Consider adding job search/filtering capabilities to the front-end application
- Evaluate potential performance optimizations for job listing endpoint with large datasets

## New Orchestrator Rule
- New orchestrator rule: Mandatory Memory Bank updates after each task
- Note: Implemented in `.roo/rules-orchestrator/prioritize_memory_bank.md`