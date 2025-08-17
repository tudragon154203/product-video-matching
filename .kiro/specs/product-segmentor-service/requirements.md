# Requirements Document

## Introduction

The Product Segmentor Service is a new microservice that will be inserted into the existing product-video matching pipeline to improve matching accuracy by focusing feature extraction on product regions while masking out people and background elements. This service will process both product catalog images and video keyframes, generating masked versions that downstream services (vision-embedding and vision-keypoint) will use instead of raw images.

## Requirements

### Requirement 1

**User Story:** As a system operator, I want the Product Segmentor Service to process product catalog images and generate masked versions, so that downstream feature extraction focuses only on product regions and improves matching accuracy.

#### Acceptance Criteria

1. WHEN a `products.image.ready` event is received THEN the system SHALL process the product image to generate a product mask
2. WHEN product segmentation is complete THEN the system SHALL publish a `products.image.masked` event with the mask path
3. WHEN all product images for a job are processed THEN the system SHALL publish a `products.images.masked.batch` event with total count
4. IF segmentation fails for an image THEN the system SHALL log the error and continue processing other images
5. WHEN processing product images THEN the system SHALL store masks in `data/masks/products/<image_id>.png` format

### Requirement 2

**User Story:** As a system operator, I want the Product Segmentor Service to process video keyframes and generate masked versions, so that video feature extraction focuses only on product regions.

#### Acceptance Criteria

1. WHEN a `video.keyframes.ready` event is received THEN the system SHALL process each keyframe to generate product masks
2. WHEN keyframe segmentation is complete THEN the system SHALL publish a `video.keyframes.masked` event with frame details and mask paths
3. WHEN all keyframes for a video are processed THEN the system SHALL publish a `video.keyframes.masked.batch` event with total count
4. IF segmentation fails for a keyframe THEN the system SHALL log the error and continue processing other keyframes
5. WHEN processing keyframes THEN the system SHALL store masks in `data/masks/frames/<frame_id>.png` format

### Requirement 3

**User Story:** As a downstream service (vision-embedding, vision-keypoint), I want to receive masked image events instead of raw image events, so that I can process product-focused features for better matching accuracy.

#### Acceptance Criteria

1. WHEN the Product Segmentor Service is deployed THEN downstream services SHALL update their event listeners to subscribe to `*.masked` events instead of `*.ready` events
2. WHEN downstream services start THEN they SHALL configure RabbitMQ bindings for the new masked event routing keys
3. WHEN a masked event is received before the watermark THEN downstream services SHALL process the masked asset
4. WHEN the watermark expires without receiving a masked event THEN downstream services SHALL process the raw asset to avoid blocking
5. WHEN processing masked assets THEN downstream services SHALL use the provided mask_path for feature extraction
6. IF a mask file is missing or corrupted THEN downstream services SHALL fallback to processing the raw asset
7. WHEN downstream services are updated THEN they SHALL stop listening to the original `*.ready` events to prevent duplicate processing

### Requirement 4

**User Story:** As a system administrator, I want the Product Segmentor Service to follow the established microservice patterns, so that it integrates seamlessly with the existing architecture.

#### Acceptance Criteria

1. WHEN the service receives SIGTERM THEN it SHALL perform graceful shutdown
2. WHEN processing events THEN the service SHALL include proper job_id and event_id tracing
3. WHEN errors occur THEN the service SHALL use structured JSON logging with appropriate levels
4. WHEN the service is deployed THEN it SHALL use the same Docker and RabbitMQ patterns as other services
5. WHEN connecting to RabbitMQ THEN the service SHALL use the established exchange and routing key patterns

### Requirement 5

**User Story:** As a developer, I want the Product Segmentor Service to have a modular segmentation engine, so that different segmentation models (RMBG, YOLO, SAM) can be easily integrated and swapped.

#### Acceptance Criteria

1. WHEN implementing segmentation logic THEN the system SHALL use a pluggable segmentation interface
2. WHEN a segmentation model is configured THEN the system SHALL load and initialize it at startup
3. WHEN segmentation is requested THEN the system SHALL use the configured model to generate masks
4. IF model loading fails THEN the system SHALL log the error and fail to start
5. WHEN different models are needed THEN the system SHALL support configuration-based model selection

### Requirement 6

**User Story:** As a system operator, I want the Product Segmentor Service to handle batch processing efficiently, so that large jobs complete in reasonable time without overwhelming system resources.

#### Acceptance Criteria

1. WHEN processing batch events THEN the system SHALL process images concurrently up to a configured limit
2. WHEN system resources are constrained THEN the system SHALL implement backpressure to prevent memory exhaustion
3. WHEN processing large batches THEN the system SHALL emit progress events for monitoring
4. IF processing is interrupted THEN the system SHALL be able to resume from the last processed item
5. WHEN batch processing completes THEN the system SHALL emit accurate completion statistics

### Requirement 7

**User Story:** As a developer, I want the existing downstream services (vision-embedding and vision-keypoint) to be updated to consume masked events, so that the new segmentation pipeline works end-to-end.

#### Acceptance Criteria

1. WHEN updating vision-embedding service THEN it SHALL modify its event handlers to listen for `products.images.masked` and `video.keyframes.masked` events
2. WHEN updating vision-keypoint service THEN it SHALL modify its event handlers to listen for `products.images.masked` and `video.keyframes.masked` events
3. WHEN downstream services process masked events THEN they SHALL read the mask_path from the event payload
4. WHEN applying masks during feature extraction THEN downstream services SHALL use the mask to focus processing on product regions
5. WHEN downstream services are updated THEN they SHALL remove the old event bindings for `*.ready` events
6. WHEN downstream services receive batch events THEN they SHALL update their completion logic to work with the new masked batch event structure

### Requirement 8

**User Story:** As a database administrator, I want the database schema to support storing mask file paths, so that the system can track and reference generated masks for each image and video frame.

#### Acceptance Criteria

1. WHEN creating the database migration THEN it SHALL add a `masked_local_path` column to the `product_images` table
2. WHEN creating the database migration THEN it SHALL add a `masked_local_path` column to the `video_frames` table
3. WHEN the Product Segmentor Service generates a mask THEN it SHALL update the corresponding database record with the mask file path
4. WHEN downstream services need mask information THEN they SHALL be able to query the mask path from the database
5. WHEN running database migrations THEN the new columns SHALL be nullable to support existing records without masks
6. WHEN the migration is applied THEN existing records SHALL have NULL values for the new masked_local_path columns