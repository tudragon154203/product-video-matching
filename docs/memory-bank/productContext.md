# Product Context

## Problem Statement
- Retailers and marketplaces need to automatically map user-generated short videos to sellable products to power attribution, discovery, and conversion
- Manual curation does not scale across platforms or catalogs
- This system automates video-to-product matching with explainable evidence, exposing:
  - A simple API for match requests and results retrieval
  - An event-driven backend that scales with catalog/video volume
  - Visual evidence artifacts to support match decisions

## User Experience
- Submit Match Request: POST `/api/v1/match` with `video_urls` or `video_ids`, optional catalog scope/filters, and an idempotent `request_id` or webhook callback
- Track Status: GET `/api/v1/jobs/{job_id}` to monitor phase progression (ingestion, vision, embedding, matching, evidence)
- Retrieve Results: GET `/api/v1/results/{job_id}` to obtain ranked product matches with scores and evidence artifacts
- Video Search (when needed): POST `/api/v1/videos/search` to look up or validate video metadata before matchmaking
- Completion Signals: Clients can rely on `matchings_process_completed` and `job_completed` events or webhooks

## Current Capabilities
- Multi-platform video ingestion (YouTube implemented, extensible to other platforms)
- Multi-marketplace product catalog acquisition (eBay US/DE/AU implemented)
- Vision processing with keypoints and embeddings
- Product segmentation for improved matching precision
- Evidence generation for explainable AI decisions
- Batch processing and pre-announce patterns for improved throughput