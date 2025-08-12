# Implementation Plan

- [ ] 1. Set up project structure and foundational components
  - Create mono-repo directory structure with services/, libs/, infra/, data/, scripts/
  - Set up base Docker images and common dependencies
  - Create shared libraries for contracts, common utilities, and vision helpers
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 2. Implement event contracts and messaging infrastructure
  - Define JSON schemas for all event types in libs/contracts/
  - Create message validation utilities in libs/common-py/
  - Implement RabbitMQ connection and publishing/consuming utilities
  - Set up topic routing and dead letter queue configuration
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 3. Create database schema and migrations
  - Set up Alembic migrations in infra/migrations/
  - Create PostgreSQL schema with pgvector extension
  - Implement database connection utilities in libs/common-py/
  - Create basic CRUD operations for all entities
  - _Requirements: 1.3, 9.1, 9.2, 9.3_

- [ ] 4. Build Orchestrator service with job management
  - Create Prefect flow definitions for job orchestration
  - Implement REST API endpoints for job control (/start-job, /status)
  - Add job state tracking in PostgreSQL
  - Create event publishing logic for initial workflow triggers
  - Add placeholder Prefect tasks that emit events without complex processing
  - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [ ] 5. Implement Catalog Collector service interface
  - Create service structure with event consumer for products.collect.request
  - Add placeholder product search logic (return mock product data)
  - Implement image download and local storage structure
  - Create products.images.ready event publishing
  - Add basic retry logic and error handling
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 6. Build Media Ingestion service interface
  - Create service structure with event consumer for videos.search.request
  - Add placeholder video search logic (return mock video data)
  - Implement basic keyframe extraction placeholder (create dummy frames)
  - Create videos.keyframes.ready event publishing
  - Add file system storage for video frames
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 7. Create Vision Embedding service with GPU support
  - Set up Docker container with PyTorch GPU base image
  - Create service structure with event consumers for image/frame ready events
  - Add placeholder embedding generation (return random vectors)
  - Implement features.ready event publishing with embedding data
  - Add GPU detection and CPU fallback logic
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 8. Implement Vision Keypoint service
  - Create service structure with event consumers for image/frame ready events
  - Add placeholder keypoint extraction (generate mock keypoint data)
  - Implement keypoint blob storage in data/kp/ directory
  - Create features.ready event publishing with keypoint paths
  - Add basic image processing utilities
  - _Requirements: 5.1, 5.3, 5.4_

- [ ] 9. Build Vector Index service with pgvector
  - Create service structure with event consumer for features.ready (products only)
  - Implement vector upsert operations using pgvector
  - Add REST API endpoint for similarity search (/search)
  - Create placeholder similarity search (return random similar items)
  - Add HNSW index management utilities
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 10. Create Matcher service with placeholder logic
  - Create service structure with event consumer for match.request
  - Add placeholder retrieval logic (call Vector Index service)
  - Implement placeholder rerank logic (return mock similarity scores)
  - Create match.result event publishing with basic scoring
  - Add configurable matching thresholds and parameters
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 11. Implement Evidence Builder service
  - Create service structure with event consumer for match.result
  - Add placeholder evidence image generation (create simple comparison images)
  - Implement evidence storage in data/evidence/ directory
  - Create match.result.enriched event publishing
  - Add basic image composition utilities
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 12. Build Results API service
  - Create FastAPI application with all required endpoints
  - Implement database queries for products, videos, matches
  - Add filtering and pagination support
  - Create static file serving for evidence images
  - Add proper HTTP status codes and error handling
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

- [ ] 13. Set up Docker Compose development environment
  - Create docker-compose.dev.yml with all services
  - Configure PostgreSQL with pgvector extension
  - Set up RabbitMQ with management interface
  - Add volume mounts for data directory and source code
  - Configure environment variables and networking
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 14. Create development utilities and scripts
  - Create Makefile with common development commands
  - Add database seeding script with sample data
  - Implement basic logging configuration across all services
  - Create environment variable templates (.env.example)
  - Add service health check endpoints
  - _Requirements: 1.5, 11.3_

- [ ] 15. Implement end-to-end smoke test
  - Create smoke test script that calls POST /start-job
  - Add verification that all events flow through the system
  - Check that placeholder results are generated and stored
  - Verify Results API returns expected data structure
  - Add basic performance timing measurements
  - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ] 16. Add error handling and monitoring foundations
  - Implement retry logic with exponential backoff across services
  - Set up dead letter queues for failed messages
  - Add structured JSON logging to all services
  - Create idempotency key handling utilities
  - Add basic metrics collection endpoints
  - _Requirements: 2.5, 3.6, 4.6, 5.6, 6.5, 7.6, 8.5_

- [ ] 17. Create integration test suite
  - Write tests for event flow between services
  - Add database integration tests with test containers
  - Create RabbitMQ integration tests
  - Test Docker Compose startup and service connectivity
  - Add API endpoint integration tests
  - _Requirements: 11.5, 11.6_

- [ ] 18. Documentation and deployment preparation
  - Create comprehensive README with setup instructions
  - Document API endpoints with OpenAPI/Swagger
  - Add service architecture diagrams
  - Create troubleshooting guide for common issues
  - Document environment variable configuration
  - _Requirements: 10.5, 11.6_