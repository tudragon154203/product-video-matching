# Matcher Service

This service is responsible for matching products with videos using a combination of deep learning embeddings and traditional computer vision techniques.

## Architecture

The service follows a modular architecture with the following components:

1. **Main Entry Point** (`main.py`): Handles service initialization, event subscription, and graceful shutdown.
2. **Configuration** (`config_loader.py`): Loads service configuration from environment variables.
3. **Business Logic** (`service.py`): Contains the main `MatcherService` class that orchestrates the matching process.
4. **Matching Engine** (`matching.py`): Contains the `MatchingEngine` class that implements the core matching algorithms.
5. **Tests** (`tests/`): Unit tests for the service components.

## Key Features

- **Modular Design**: Separation of concerns with distinct modules for different responsibilities
- **Hybrid Matching Approach**: Combines deep learning embeddings with traditional computer vision techniques
- **Dependency Injection**: Makes the service testable
- **Proper Error Handling**: Comprehensive error handling and logging
- **Resource Management**: Proper cleanup of resources on shutdown

## How It Works

1. The service subscribes to `match.request` events from the message broker
2. When a match request is received, it retrieves the relevant products and videos for the job
3. It performs matching between all product-video pairs using the matching engine
4. For each match found, it creates a match record in the database and publishes a `match.result` event

## Matching Process

The matching process involves several steps:

1. **Vector Retrieval**: Uses embeddings to find similar video frames for each product image
2. **Keypoint Matching**: Applies RANSAC-based keypoint matching for geometric verification
3. **Score Aggregation**: Combines multiple similarity scores with weighted averaging
4. **Acceptance Filtering**: Applies threshold-based filtering to ensure high-quality matches

## Running Tests

```bash
python -m pytest tests/ -v
```