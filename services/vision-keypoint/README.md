# Vision Keypoint Microservice

## Overview
This microservice extracts traditional computer vision features (keypoints and descriptors) from images and video frames. These features are used for geometric matching and verification.

## Functionality
- Detects robust keypoints and computes descriptors (e.g., AKAZE, SIFT).
- Processes product images and video frames to extract local features.
- Publishes keypoint data for use by the Matcher service.

## In/Out Events
### Input Events
- `ImageForKeypointExtraction`: Event containing an image (product or video frame) for keypoint extraction.
  - Data: `{"image_id": "img-001", "image_url": "http://example.com/image.jpg", "type": "video_frame"}`

### Output Events
- `ProductKeypointsReady`: Event indicating that product keypoints have been extracted.
  - Data: `{"product_id": "prod-456", "keypoints": [...], "descriptors": [...]}`
- `VideoFrameKeypointsReady`: Event indicating that video frame keypoints have been extracted.
  - Data: `{"video_id": "vid-789", "frame_number": 10, "keypoints": [...], "descriptors": [...]}`

## Current Progress
- AKAZE keypoint detection and descriptor computation implemented.
- Basic integration with image processing utilities.

## What's Next
- Explore other keypoint detectors and descriptors (e.g., SIFT, ORB).
- Optimize keypoint extraction for performance on high-resolution images.
- Implement feature matching and outlier rejection within the service (if applicable).