# System Patterns

## Architecture
- Event‑driven pipeline coordinated by the Main API using JSON Schema contracts in `libs/contracts`. Work is represented as jobs and phases; services publish/consume events over the broker to advance the pipeline. Core flow:
  - Request Intake: Client calls Main API; service emits `match_request` and derives initial intents (e.g., `products_collect_request`, `videos_search_request`).
  - Catalog Ingestion: Dropship‑Product‑Finder collects catalog items; downstream emits `products_images_ready` or `products_images_masked_batch` as assets prepare.
  - Media Ingestion: Video‑Crawler fetches videos and extracts frames; emits `videos_keyframes_ready` (and batch variants) and, when applicable, masked keyframes.
  - Vision Processing: Vision‑Keypoint produces keypoints (`image_keypoint_ready` / `image_keypoints_completed`). Vision‑Embedding generates embeddings (`image_embedding_ready`, `video_embedding_ready`, `*_embeddings_completed`).
  - Matching: Matcher consumes product and video embeddings directly from Qdrant vector database and outputs `match_result` and pipeline completion signals (`match_request_completed`, `job_completed`).
  - Evidence: Evidence‑Builder compiles visual/metric evidence and emits `evidences_generation_completed`.
  - Results Serving: Results‑API aggregates and exposes final results for retrieval.
  - Batching and Pre‑announce: Contracts include multiple‑event and pre‑announce patterns (sprint 6.2) to improve throughput and reduce tail latency.

## Key Components
- `main-api`: Request intake, phase orchestration, results aggregation and retrieval, LLM prompt/query fallback (Gemini-first with Ollama fallback).
- `video-crawler`: Cross-platform media acquisition (YouTube implemented) and keyframe preparation.
- `vision-keypoint`: Keypoint detection and geometric features.
- `vision-embedding`: Embedding generation for images/videos.
- `matcher`: Ranking across product/video embeddings with direct integration with Qdrant vector database; emits matches and completion events.
- `product-segmentor`: Product region segmentation to improve downstream signal.
- `evidence-builder`: Builds explainable visual artifacts tied to matches. This service is crucial for generating a *new* composite image that visually represents a match, often involving:
    *   **Image Composition:** Combining the original product image and the relevant video frame.
    *   **Feature Overlay:** Highlighting matched features (e.g., keypoints, bounding boxes) on both source images.
    *   **Information Overlay:** Adding metadata like match score or timestamp.
    This specialized image processing distinguishes it from simply retrieving or displaying existing images, ensuring separation of concerns and independent scalability from the `matcher` service.
- `dropship-product-finder`: Catalog acquisition from marketplaces (eBay US/DE/AU implemented).
- Shared libs: `contracts` (JSON Schemas), `common-py`, `vision-common` (for job progress tracking).

## Design Patterns
- Job Progress Management: All vision services use `vision-common` library for consistent progress tracking
- Event-Driven Communication: Services communicate via RabbitMQ with strict JSON Schema contracts
- Batch Processing: Multiple events and pre-announce patterns for improved throughput
- Direct Database Access: Matcher reads embeddings directly from Postgres (no vector-index service)
- API Consistency: Job listing endpoints follow established patterns for dependency injection, query validation, and response schemas