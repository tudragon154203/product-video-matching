# Implementation Plan

- [ ] 1. Create database migration for masked_local_path columns
  - Add masked_local_path column to product_images table
  - Add masked_local_path column to video_frames table  
  - Add indexes for mask path queries
  - Update Pydantic models in common_py to include masked_local_path fields
  - _Requirements: 8.1, 8.2, 8.5, 8.6_

- [ ] 2. Create new event schema contracts
  - Create products_image_masked.json schema file
  - Create products_images_masked_batch.json schema file
  - Create video_keyframes_masked.json schema file
  - Create video_keyframes_masked_batch.json schema file
  - _Requirements: 1.2, 1.3, 2.2, 2.3_

- [ ] 3. Implement segmentation interface and RMBG implementation
  - Create abstract SegmentationInterface class
  - Implement RMBGSegmentor class using Hugging Face transformers
  - Add model initialization and cleanup methods
  - Write unit tests for segmentation interface
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 4. Create Product Segmentor Service core structure
  - Create service directory structure following established patterns
  - Implement config_loader.py with ProductSegmentorConfig
  - Create main.py with service lifecycle management
  - Add requirements.txt with necessary dependencies
  - _Requirements: 4.3, 4.4, 4.5_

- [ ] 5. Implement file management for mask storage
  - Create FileManager class for mask file operations
  - Implement mask directory creation (data/masks/products/, data/masks/frames/)
  - Add atomic file save operations with proper naming
  - Write unit tests for file operations
  - _Requirements: 1.5, 2.5_

- [ ] 6. Implement ProductSegmentorService business logic
  - Create ProductSegmentorService class with database and messaging integration
  - Implement image loading and segmentation coordination
  - Add mask file saving and database record updates
  - Implement batch completion tracking logic
  - Handle edge cases for empty batches (count=0)
  - _Requirements: 1.1, 1.4, 2.1, 2.4, 6.1, 6.5_

- [ ] 7. Implement event handlers for product images
  - Create ProductSegmentorHandler class
  - Implement handle_products_images_ready method with event validation
  - Implement handle_products_images_ready_batch method
  - Add proper error handling and logging for segmentation failures
  - _Requirements: 1.1, 1.2, 1.3, 4.2, 4.3_

- [ ] 8. Implement event handlers for video keyframes
  - Implement handle_video_keyframes_ready method
  - Implement handle_video_keyframes_ready_batch method
  - Handle multiple frames per video in single event
  - Add batch completion tracking for video processing
  - _Requirements: 2.1, 2.2, 2.3, 4.2, 4.3_

- [ ] 9. Add concurrent processing and resource management
  - Implement concurrent image processing with configurable limits
  - Add backpressure handling to prevent memory exhaustion
  - Implement processing timeout and retry logic
  - Write integration tests for concurrent processing
  - _Requirements: 6.1, 6.2, 6.4_

- [ ] 10. Create Docker configuration and deployment setup
  - Create Dockerfile following established service patterns
  - Add docker-compose service definition
  - Configure RabbitMQ routing keys and exchanges
  - Set up environment variable configuration
  - _Requirements: 4.4, 4.5_

- [ ] 11. Update vision-embedding service for masked events
  - Modify event handlers to subscribe to products.images.masked and video.keyframes.masked
  - Update RabbitMQ bindings to new masked event routing keys
  - Implement watermark timeout logic with fallback to raw images
  - Remove old *.ready event bindings
  - Add mask path processing in feature extraction
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.7_

- [ ] 12. Update vision-keypoint service for masked events
  - Modify event handlers to subscribe to masked events instead of ready events
  - Update RabbitMQ bindings for new routing keys
  - Implement watermark timeout and fallback logic
  - Remove old event bindings for *.ready events
  - Add mask application during keypoint extraction
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.7_

- [ ] 13. Write comprehensive tests for the segmentation service
  - Create unit tests for all service components
  - Write integration tests for database operations
  - Add end-to-end tests for event processing flow
  - Test edge cases including empty batches and missing files
  - _Requirements: 1.4, 2.4, 6.4_

- [ ] 14. Deploy and integrate the complete segmentation pipeline
  - Run database migration to add masked_local_path columns
  - Deploy Product Segmentor Service with RMBG model
  - Deploy updated vision-embedding and vision-keypoint services
  - Verify end-to-end event flow from collection to feature extraction
  - Monitor processing performance and error rates
  - _Requirements: 8.1, 8.2, 4.1, 3.5, 3.6_