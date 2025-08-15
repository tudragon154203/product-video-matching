---
inclusion: fileMatch
fileMatchPattern: '*vision*'
---

# Vision Processing Guidelines

## Computer Vision Standards
- **Image Preprocessing**: Normalize images to consistent format (RGB, 224x224 for CLIP)
- **Feature Extraction**: Use CLIP for embeddings, AKAZE/SIFT for keypoints
- **GPU Acceleration**: Implement with CPU fallback for production reliability
- **Batch Processing**: Process images in batches for efficiency

## Embedding Generation
- **Model**: Use `clip-vit-b32` as default embedding model
- **Normalization**: L2 normalize embeddings for cosine similarity
- **Storage**: Store embeddings as float arrays in PostgreSQL
- **Caching**: Cache model weights to avoid repeated downloads

## Keypoint Matching
- **Algorithms**: AKAZE for speed, SIFT for accuracy
- **RANSAC**: Use for geometric verification with min 4 inliers
- **Thresholds**: 
  - `INLIERS_MIN`: 0.35 (minimum inliers ratio)
  - `SIM_DEEP_MIN`: 0.82 (minimum embedding similarity)
- **Filtering**: Remove low-quality keypoints before matching

## Matching Pipeline
1. **Vector Search**: Use pgvector for top-K candidate retrieval
2. **Embedding Similarity**: Cosine similarity between CLIP features
3. **Geometric Verification**: SIFT + RANSAC for spatial consistency
4. **Score Fusion**: Combine embedding + keypoint scores
5. **Filtering**: Apply acceptance threshold (default: 0.80)

## Performance Optimization
- **Parallel Processing**: Process multiple images simultaneously
- **Memory Management**: Clear GPU memory between batches
- **Index Optimization**: Use HNSW index for vector search
- **Caching**: Cache frequently accessed embeddings

## Error Handling
- **GPU Fallback**: Automatically switch to CPU if GPU unavailable
- **Image Validation**: Check image format and size before processing
- **Memory Limits**: Handle out-of-memory errors gracefully
- **Timeout Handling**: Set reasonable timeouts for processing operations