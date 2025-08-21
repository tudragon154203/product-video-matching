# Active Context

## Current Focus
- Sprint 9: ✅ COMPLETED - Retired the dedicated vector-index service and simplified the matcher to consume embeddings directly from storage/DB. Updated contracts and consumers to stop emitting/consuming vector-index events. Made Qdrant infra optional/off by default in dev.
- Current LLM strategy: Gemini-first with Ollama fallback (implemented in main-api/services/llm_service.py)
- 2025-08-18: Completed removal of published_at column from database schema and YouTube crawler
- 2025-08-19: ✅ COMPLETED - Updated memory bank with current project state and recent sprint completions
- Current focus: eBay integration for dropship-product-finder (30% complete) and YouTube crawler implementation for video-crawler service (85% complete)

## Active Development Areas
- **Dropship Product Finder**: eBay integration implementation (OAuth, Browse API, image processing)
  * eBay Browse API integration
  * Product deduplication by EPID
  * Image processing pipeline
  * Database schema updates
- **Video Crawler**: YouTube search and download functionality using yt-dlp
- **Vision Services**: Consistent use of vision-common library across all vision services

## Recent Completions
- Sprint 9: Vector-index service retirement and matcher simplification
- Database schema updates (removed published_at column)
- Memory bank automation rule implementation
- Vision services refactoring to use vision-common library
- YouTube crawler core functionality implemented

## Next Steps
- Complete eBay integration phases (OAuth implementation, Browse API integration, image pipeline)
- Implement YouTube crawler with proper search and download functionality
- Strengthen integration tests across the updated pipeline
- Update documentation to reflect current architecture and capabilities
- Monitor performance after vector-index service removal
- Complete eBay integration missing components
- Finalize YouTube crawler testing

## New Orchestrator Rule
- New orchestrator rule: Mandatory Memory Bank updates after each task
- Note: Implemented in `.roo/rules-orchestrator/prioritize_memory_bank.md`