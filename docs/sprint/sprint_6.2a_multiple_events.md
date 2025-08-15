Summary: Handling Multiple Completion Events Issue
Problem
The vision-embedding and vision-keypoint services are publishing multiple image.embeddings.completed and image.keypoints.completed events for a single job instead of one aggregated event per job. This causes:

Dozens of duplicate events in logs
Database warnings about multiple phase events
Inefficient event processing
Root Cause
Each individual products.images.ready event triggers a completion event with total=1 and done=1, treating each image as a separate "job" instead of aggregating all images for the actual job.

Solution Approach
Create a job-level coordination mechanism where vision services wait to receive all images for a job before publishing completion events.

Implementation Steps
1. Create New Event Schema
File: libs/contracts/contracts/schemas/products_images_ready_batch.json
Purpose: Notify vision services about total image count for a job
Schema:
{
  "job_id": "string",
  "event_id": "string", 
  "total_images": "integer (minimum: 0)"
}
2. Modify Dropship-Product-Finder Service
File: services/dropship-product-finder/services/service.py
Changes:
After publishing products.collections.completed, query database for total image count
Publish new products.images.ready.batch event with total count
This provides vision services with expected image count upfront
3. Update Vision Services (Both Embedding & Keypoint)
Files:
services/vision-embedding/services/service.py
services/vision-keypoint/services/service.py
Changes:
Add job_image_counts: Dict[str, int] to track expected counts per job
Replace handle_products_collections_completed() with handle_products_images_ready_batch()
Store total image count when batch event received
Use stored count instead of expected_count=1 in progress tracking
Only publish completion event when done >= expected for the job
4. Update Event Subscriptions
Files:
services/vision-embedding/main.py
services/vision-keypoint/main.py
Changes:
Replace subscription from products.collections.completed to products.images.ready.batch
This avoids conflict with main-api consuming the collections.completed event
5. Update Event Handlers
Files:
services/vision-embedding/handlers/embedding_handler.py
services/vision-keypoint/handlers/keypoint_handler.py
Changes:
Replace @validate_event("products_collections_completed") with @validate_event("products_images_ready_batch")
Update method names accordingly
Expected Result
One image.embeddings.completed event per job (instead of dozens)
One image.keypoints.completed event per job (instead of dozens)
Clean logs without duplicate event warnings
Proper job-level aggregation of image processing
Key Design Principle
The products.images.ready.batch event is specifically for vision service coordination and doesn't interfere with the main-api's use of products.collections.completed for phase management.

Testing
Run smoke test to verify:

Jobs complete successfully
Only one completion event per job type in logs
No "MULTIPLE phase events" warnings in database logs