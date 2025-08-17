---
inclusion: always
---

# Product-Video Matching System Architecture

## System Overview
This is an event-driven microservices system for matching e-commerce products with video content using computer vision and deep learning. The system follows an image-first approach with 95%+ precision at score ≥ 0.80.

## Core Architecture Principles
- **Event-driven**: All services communicate via RabbitMQ events
- **Microservices**: Each service has a single responsibility
- **Image-first matching**: Deep learning embeddings + traditional CV techniques
- **GPU acceleration**: With CPU fallback for embedding generation
- **Vector similarity**: PostgreSQL + pgvector for efficient search

## Service Structure
```
services/
├── main-api/              # Job orchestration & state machine
├── results-api/           # REST API for results
├── dropship-product-finder/  # Product collection (Amazon/eBay)
├── video-crawler/         # Video processing (YouTube)
├── vision-embedding/      # CLIP embeddings generation
├── vision-keypoint/       # AKAZE/SIFT keypoint extraction
├── matcher/               # Core matching logic
└── evidence-builder/      # Visual evidence generation
```

## Shared Libraries
```
libs/
├── contracts/             # Event schemas & validation
├── common-py/            # Common utilities & database
└── vision-common/        # Vision processing utilities
```

## Data Flow
1. **Collection Phase**: Products + Videos collected in parallel
2. **Feature Extraction**: Embeddings + Keypoints extracted in parallel
3. **Vector Indexing**: Features stored in pgvector
4. **Matching**: Cosine similarity + geometric verification
5. **Evidence**: Visual proof generation
6. **Results**: Available via REST API

## Technology Stack
- **Language**: Python 3.10+
- **Framework**: FastAPI (APIs), asyncio (workers)
- **Database**: PostgreSQL + pgvector
- **Message Broker**: RabbitMQ
- **Vision**: OpenCV, CLIP, AKAZE/SIFT
- **Infrastructure**: Docker Compose