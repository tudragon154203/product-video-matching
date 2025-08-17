# Vision Embedding Service

This service extracts visual embeddings from product images and video frames using CLIP models.

## Architecture

The service follows a modular architecture with the following components:

1. **Main Entry Point** (`main.py`): Handles service initialization, event subscription, and graceful shutdown.
2. **Configuration** (`config_loader.py`): Loads service configuration from environment variables.
3. **Business Logic** (`service.py`): Contains the main `VisionEmbeddingService` class that orchestrates embedding extraction.
4. **Embedding Extraction** (`embedding.py`): Contains the `EmbeddingExtractor` class that handles CLIP model operations.
5. **Tests** (`tests/`): Unit tests for the service components.

## Key Features

- **Modular Design**: Separation of concerns with distinct modules for different responsibilities
- **CLIP Model Support**: Uses CLIP models for state-of-the-art visual embedding extraction
- **GPU Acceleration**: Automatically uses GPU when available for faster processing
- **Event-Driven**: Subscribes to image and frame ready events for automatic processing
- **Dependency Injection**: Makes the service testable
- **Proper Error Handling**: Comprehensive error handling and logging
- **Resource Management**: Proper cleanup of resources on shutdown

## Event Handling

The service subscribes to:
- `products.image.ready` events for product image embedding extraction
- `videos.keyframes.ready` events for video frame embedding extraction

For each event, it:
1. Extracts RGB and grayscale embeddings using CLIP
2. Updates the database with the embeddings
3. Publishes a `features.ready` event for downstream processing

## Running Tests

```bash
python -m pytest tests/ -v
```