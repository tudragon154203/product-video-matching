# Evidence Builder Service

This service is responsible for generating visual evidence images for product-video matches.

## Architecture

The service follows a modular architecture with the following components:

1. **Main Entry Point** (`main.py`): Handles service initialization, event subscription, and graceful shutdown.
2. **Configuration** (`config_loader.py`): Loads service configuration from environment variables.
3. **Business Logic** (`service.py`): Contains the main `EvidenceBuilderService` class that orchestrates evidence generation.
4. **Evidence Generation** (`evidence.py`): Contains the `EvidenceGenerator` class that creates visual evidence images.
5. **Tests** (`tests/`): Unit tests for the service components.

## Key Features

- **Modular Design**: Separation of concerns with distinct modules for different responsibilities
- **Dependency Injection**: Makes the service testable
- **Proper Error Handling**: Comprehensive error handling and logging
- **Resource Management**: Proper cleanup of resources on shutdown

## How It Works

1. The service subscribes to `match.result` events from the message broker
2. When a match result is received, it retrieves the product image and video frame information from the database
3. It generates a visual evidence image showing the matched product and video frame side-by-side
4. The evidence image is saved to disk and the match record is updated with the evidence path
5. An `evidences.generation.completed` event is published to signal completion of evidence generation for the job

## Running Tests

```bash
python -m pytest tests/ -v
```