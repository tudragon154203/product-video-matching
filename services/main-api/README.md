# Main API Microservice

## Overview
This microservice acts as the central job orchestration and state management component of the Product-Video Matching System. It provides the primary interface for initiating and managing matching tasks.

## Functionality
- Orchestrates the workflow of product-video matching jobs.
- Manages the state and progress of ongoing matching tasks.
- Provides REST endpoints for job submission and status retrieval.

## In/Out Events
### Input Events
- `JobSubmissionRequest`: API request to start a new product-video matching job.
  - Data: `{"product_url": "http://example.com/product", "video_url": "http://example.com/video"}`

### Output Events
- `ProductIngestionInitiated`: Event to start the product collection process.
  - Data: `{"job_id": "job-001", "product_url": "http://example.com/product"}`
- `VideoIngestionInitiated`: Event to start the video processing process.
  - Data: `{"job_id": "job-001", "video_url": "http://example.com/video"}`

## Current Progress
- Core job submission and status tracking implemented.
- Basic integration with product and video ingestion services.

## What's Next
- Implement more granular job control and pausing/resuming.
- Enhance error reporting and recovery mechanisms.
- Scale API for higher throughput.