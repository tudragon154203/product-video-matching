# Vision Embedding Microservice

## Overview
This microservice generates deep learning features (embeddings) from images and video frames. These embeddings are crucial for semantic similarity matching between products and video content.

## Functionality
- Utilizes pre-trained deep learning models (e.g., CLIP) to generate embeddings.
- Processes product images and video frames to extract high-dimensional feature vectors.
- Publishes embeddings for use by the Matcher service.

## In/Out Events
### Input Events
- `ImageForEmbedding`: Event containing an image (product or video frame) for embedding generation.
  - Data: `{"image_id": "img-001", "image_url": "http://example.com/image.jpg", "type": "product"}`

### Output Events
- `ProductEmbeddingReady`: Event indicating that product embeddings have been generated.
  - Data: `{"product_id": "prod-456", "embedding_vector": [0.1, 0.2, ...]}`
- `VideoFrameEmbeddingReady`: Event indicating that video frame embeddings have been generated.
  - Data: `{"video_id": "vid-789", "frame_number": 10, "embedding_vector": [0.3, 0.4, ...]}`

## Current Progress
- CLIP model integration for embedding generation.
- GPU acceleration setup for faster processing.

## What's Next
- Explore and integrate other state-of-the-art embedding models.
- Optimize embedding generation pipeline for large-scale data.
- Implement dynamic model loading and updating.