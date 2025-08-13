# Media Ingestion Service

This service is responsible for searching, downloading, and processing videos from platforms like YouTube and Bilibili.

## Architecture

The service follows a modular architecture with the following components:

1. **Main Entry Point** (`main.py`): Handles service initialization, event subscription, and graceful shutdown.
2. **Configuration** (`config_loader.py`): Loads service configuration from environment variables.
3. **Business Logic** (`service.py`): Contains the main `MediaIngestionService` class that orchestrates video processing.
4. **Video Ingestion** (`ingestion.py`): Contains the `VideoIngestion` class that handles video search and keyframe extraction.
5. **Tests** (`tests/`): Unit tests for the service components.

## Key Features

- **Modular Design**: Separation of concerns with distinct modules for different responsibilities
- **Multi-Platform Support**: Supports YouTube and Bilibili (easily extensible for other platforms)
- **Dependency Injection**: Makes the service testable
- **Proper Error Handling**: Comprehensive error handling and logging
- **Resource Management**: Proper cleanup of resources on shutdown

## How It Works

1. The service subscribes to `videos.search.request` events from the message broker
2. When a video search request is received, it searches for videos on the specified platforms
3. For each video found, it downloads the video and extracts keyframes
4. The extracted keyframes are saved to disk and database records are created
5. A `videos.keyframes.ready` event is published for each processed video

## Running Tests

```bash
python -m pytest tests/ -v
```