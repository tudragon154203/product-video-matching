# Matcher Microservice

## Overview
This microservice contains the core logic for matching products with video content. It leverages deep learning embeddings and traditional computer vision techniques to identify visual similarities.

## Functionality
- Compares product embeddings with video frame embeddings.
- Applies computer vision algorithms (e.g., AKAZE/SIFT + RANSAC) for precise matching.
- Determines the confidence score of potential matches.

## In/Out Events
### Input Events
- `ProductEmbeddingReady`: Event indicating that product embeddings are available for matching.
  - Data: `{"product_id": "prod-456", "embedding_vector": [0.1, 0.2, ...]}`
- `VideoFrameEmbeddingReady`: Event indicating that video frame embeddings are available.
  - Data: `{"video_id": "vid-789", "frame_number": 10, "embedding_vector": [0.3, 0.4, ...]}`

### Output Events
- `MatchFound`: Event indicating a successful match between a product and a video segment.
  - Data: `{"match_id": "abc-123", "product_id": "prod-456", "video_id": "vid-789", "timestamp": 123.45, "confidence": 0.95}`

## Current Progress
- Initial implementation of CLIP embedding similarity matching.
- Integration of AKAZE/SIFT for keypoint matching.

## What's Next
- Optimize matching algorithms for speed and accuracy.
- Explore advanced matching techniques and models.
- Implement batch processing for improved efficiency.