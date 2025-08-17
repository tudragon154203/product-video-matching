# Requirements Document

## Introduction

This document outlines the requirements for Sprint 1 of the Event-Driven Microservices system for Product ↔ Video Matching. The system uses an image-first approach to match Amazon/eBay products with Vietnamese/Chinese videos based on visual similarity. Sprint 1 focuses on building a minimal viable product (MVP) that can process a keyword, collect products from Amazon/eBay, find relevant YouTube videos, and return matching pairs with evidence images.

The system follows an event-driven microservices architecture using RabbitMQ for messaging, PostgreSQL with pgvector for storage, and Docker Compose for local development.

## Requirements

### Requirement 1: System Architecture Setup

**User Story:** As a developer, I want to set up the foundational microservices architecture, so that I can build and deploy the product-video matching system locally.

#### Acceptance Criteria

1. WHEN the system is initialized THEN it SHALL create a mono-repo structure with services, libs, infra, and data directories
2. WHEN docker-compose is executed THEN it SHALL start PostgreSQL, RabbitMQ, and all microservices
3. WHEN the system starts THEN it SHALL establish database connections with pgvector extension enabled
4. WHEN services communicate THEN they SHALL use RabbitMQ message broker with proper topic routing
5. IF any service fails to start THEN the system SHALL log clear error messages and retry with exponential backoff

### Requirement 2: Event Contracts and Messaging

**User Story:** As a system architect, I want standardized event contracts across all services, so that microservices can communicate reliably and data validation is consistent.

#### Acceptance Criteria

1. WHEN events are published THEN they SHALL conform to predefined JSON schemas stored in libs/contracts/
2. WHEN a service receives an event THEN it SHALL validate the event against the corresponding schema
3. WHEN validation fails THEN the service SHALL reject the event and log the validation error
4. WHEN events are processed THEN they SHALL include proper correlation IDs for tracing
5. IF message processing fails 3 times THEN the message SHALL be moved to a dead letter queue

### Requirement 3: Product Catalog Collection

**User Story:** As a system user, I want to collect product information from Amazon and eBay based on industry keywords, so that I have a dataset of products to match against videos.

#### Acceptance Criteria

1. WHEN a products.collect.request event is received THEN the system SHALL search Amazon and eBay for the specified industry keyword
2. WHEN products are found THEN the system SHALL collect top-K products (configurable, default 10 each platform)
3. WHEN product images are downloaded THEN they SHALL be stored locally in data/products/{product_id}/ directory
4. WHEN images are processed THEN they SHALL be normalized and standardized to consistent format
5. WHEN collection is complete THEN the system SHALL publish products.image.ready events for each image
6. IF product collection fails THEN the system SHALL retry up to 3 times before moving to DLQ

### Requirement 4: Video Content Ingestion

**User Story:** As a system user, I want to find and process relevant YouTube videos based on industry keywords, so that I have video frames to match against product images.

#### Acceptance Criteria

1. WHEN a videos.search.request event is received THEN the system SHALL search YouTube for videos matching the industry keyword
2. WHEN videos are found THEN the system SHALL download the videos locally
3. WHEN videos are processed THEN the system SHALL extract 3-8 keyframes per video, filtering out blurry frames
4. WHEN keyframes are extracted THEN they SHALL be stored in data/videos/{video_id}/frames/ directory
5. WHEN frame extraction is complete THEN the system SHALL publish videos.keyframes.ready events
6. IF video processing fails THEN the system SHALL log the error and continue with other videos

### Requirement 5: Visual Feature Extraction

**User Story:** As a system developer, I want to extract visual features from product images and video frames, so that I can perform similarity matching between them.

#### Acceptance Criteria

1. WHEN products.image.ready or videos.keyframes.ready events are received THEN the system SHALL extract visual embeddings using CLIP model
2. WHEN images are processed THEN the system SHALL generate both RGB and grayscale embeddings
3. WHEN keypoint extraction is performed THEN the system SHALL use AKAZE/SIFT algorithms and store results as kp_blob files
4. WHEN feature extraction is complete THEN the system SHALL publish features.ready events with embedding data
5. WHEN GPU is available THEN the system SHALL use GPU acceleration for embedding generation
6. IF GPU is not available THEN the system SHALL fallback to CPU processing with appropriate performance adjustments

### Requirement 6: Vector Indexing and Search

**User Story:** As a system component, I want to efficiently store and search visual embeddings, so that I can quickly find similar images during the matching process.

#### Acceptance Criteria

1. WHEN features.ready events are received for product images THEN the system SHALL upsert embeddings into pgvector HNSW index
2. WHEN similarity search is requested THEN the system SHALL return top-K most similar embeddings using cosine similarity
3. WHEN vector operations are performed THEN they SHALL support both RGB and grayscale embeddings
4. WHEN indexing is complete THEN the system SHALL maintain metadata linking embeddings to original images
5. IF vector operations fail THEN the system SHALL retry with exponential backoff up to 3 times

### Requirement 7: Image Matching and Scoring

**User Story:** As a system user, I want to match product images with video frames based on visual similarity, so that I can identify products appearing in videos.

#### Acceptance Criteria

1. WHEN match.request events are received THEN the system SHALL perform retrieval using ANN search on embeddings
2. WHEN candidates are retrieved THEN the system SHALL rerank using keypoint matching with RANSAC algorithm
3. WHEN pair scoring is calculated THEN it SHALL use weighted combination: 35% embedding similarity + 55% keypoint similarity + 10% edge similarity
4. WHEN product-video matching is performed THEN the system SHALL aggregate M images × N frames and apply acceptance rules
5. WHEN matches are found THEN the system SHALL publish match.result events with scores ≥ 0.80
6. IF no matches meet the threshold THEN the system SHALL log the result without publishing match events

### Requirement 8: Evidence Generation

**User Story:** As a system user, I want visual evidence of matches between products and videos, so that I can verify the accuracy of the matching results.

#### Acceptance Criteria

1. WHEN match.result events are received THEN the system SHALL generate side-by-side comparison images
2. WHEN evidence is created THEN it SHALL overlay keypoint matches and inliers from RANSAC
3. WHEN evidence images are generated THEN they SHALL be stored in data/evidence/{match_id}.jpg
4. WHEN evidence creation is complete THEN the system SHALL publish match.result.enriched events
5. IF evidence generation fails THEN the system SHALL log the error but still preserve the match result

### Requirement 9: Results API

**User Story:** As an external system (n8n/UI), I want to query matching results through a REST API, so that I can retrieve and display product-video matches.

#### Acceptance Criteria

1. WHEN GET /results is called THEN the system SHALL return a list of matches filtered by minimum score
2. WHEN GET /products/{id} is called THEN the system SHALL return detailed product information
3. WHEN GET /videos/{id} is called THEN the system SHALL return detailed video information  
4. WHEN GET /matches/{match_id} is called THEN the system SHALL return match details including evidence path
5. WHEN API requests include industry filter THEN the system SHALL filter results by industry keyword
6. IF requested resources don't exist THEN the system SHALL return appropriate HTTP 404 responses

### Requirement 10: Job Orchestration

**User Story:** As a system user, I want to initiate and track end-to-end matching jobs, so that I can process industry keywords and monitor progress.

#### Acceptance Criteria

1. WHEN POST /orchestrator/start-job is called THEN the system SHALL create a new job and publish initial collection events
2. WHEN a job is started THEN the system SHALL return a unique job_id for tracking
3. WHEN GET /status/{job_id} is called THEN the system SHALL return current phase, progress percentage, and processing counts
4. WHEN job processing is complete THEN all intermediate events SHALL have been processed and results available via API
5. IF job processing encounters errors THEN the system SHALL track error states and provide meaningful status updates

### Requirement 11: System Integration and Quality

**User Story:** As a developer, I want end-to-end system validation, so that I can ensure the complete pipeline works correctly from keyword input to match results.

#### Acceptance Criteria

1. WHEN the smoke test is executed THEN it SHALL successfully process a test keyword through the entire pipeline
2. WHEN end-to-end processing completes THEN it SHALL produce at least one valid match with score ≥ 0.80
3. WHEN matches are generated THEN they SHALL include evidence images demonstrating visual similarity
4. WHEN system performance is measured THEN it SHALL achieve precision ≥95% for matches with score ≥ 0.80
5. WHEN the system processes requests THEN it SHALL handle throughput of ~5k keyframes per day on CPU
6. IF any component fails during integration testing THEN the system SHALL provide clear error messages and recovery instructions