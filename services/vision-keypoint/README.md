# Vision Keypoint Service

This service extracts keypoint descriptors from product images and video frames using AKAZE and SIFT algorithms.

## Architecture

The service follows a modular architecture with the following components:

1. **Main Entry Point** (`main.py`): Handles service initialization, event subscription, and graceful shutdown.
2. **Configuration** (`config_loader.py`): Loads service configuration from environment variables.
3. **Business Logic** (`service.py`): Contains the main `VisionKeypointService` class that orchestrates keypoint extraction.
4. **Keypoint Extraction** (`keypoint.py`): Contains the `KeypointExtractor` class that handles AKAZE and SIFT operations.
5. **Tests** (`tests/`): Unit tests for the service components.

## Key Features

- **Modular Design**: Separation of concerns with distinct modules for different responsibilities
- **Dual Algorithm Support**: Uses both AKAZE (faster) and SIFT (more robust) algorithms
- **Event-Driven**: Subscribes to image and frame ready events for automatic processing
- **Dependency Injection**: Makes the service testable
- **Proper Error Handling**: Comprehensive error handling and logging
- **Resource Management**: Proper cleanup of resources on shutdown

## Event Handling

The service subscribes to:
- `products.images.ready` events for product image keypoint extraction
- `videos.keyframes.ready` events for video frame keypoint extraction

For each event, it:
1. Extracts keypoints and descriptors using AKAZE or SIFT
2. Updates the database with the keypoint file path
3. Publishes a `features.ready` event for downstream processing

## Running Tests

```bash
python -m pytest tests/ -v
```