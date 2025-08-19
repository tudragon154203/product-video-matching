# Active Context

## Current Focus
- Sprint 9: Retire the dedicated vector‑index service and simplify the matcher to consume embeddings directly from storage/DB. Update contracts and consumers to stop emitting/consuming vector‑index events. Keep Qdrant infra optional/off by default in dev. Ensure performance parity using batch and pre‑announce flows introduced in sprint 6.2.
- Current LLM strategy: Gemini-first with Ollama fallback (implemented in main-api/services/llm_service.py)
- 2025-08-18: Completed removal of published_at column from database schema and YouTube crawler
- Current focus: Ensuring all vision services consistently use vision-common library for progress tracking and event management

## Next Steps
- Finalize schema deprecations and emit compatibility notices for retired events.
- Update infra compose and service configs to make vector index optional and disabled by default.
- Clean up dead code paths and remove vector‑index service references across services and docs.
- Strengthen integration tests across ingestion → embeddings → matcher → results.
- Update dashboards/metrics to reflect the new matching path and evidence timing.

## New Orchestrator Rule
- New orchestrator rule: Mandatory Memory Bank updates after each task
- Note: Implemented in `.roo/rules-orchestrator/prioritize_memory_bank.md`