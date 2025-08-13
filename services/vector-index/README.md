# Vector Index Service

This service provides vector similarity search capabilities for product images using pgvector.

## Architecture

The service follows a modular architecture with the following components:

1. **Main Entry Point** (`main.py`): Defines the FastAPI application and API endpoints.
2. **Configuration** (`config_loader.py`): Loads service configuration from environment variables.
3. **Business Logic** (`service.py`): Contains the main `VectorIndexService` class that implements the core functionality.
4. **Vector Operations** (`vector_ops.py`): Contains the `VectorOperations` class that handles vector operations with pgvector.
5. **Tests** (`tests/`): Unit tests for the service components.

## Key Features

- **Modular Design**: Separation of concerns with distinct modules for different responsibilities
- **FastAPI Framework**: High-performance REST API implementation
- **Event-Driven**: Subscribes to features ready events for automatic indexing
- **Dependency Injection**: Makes the service testable
- **Proper Error Handling**: Comprehensive error handling and logging
- **Resource Management**: Proper cleanup of resources on shutdown

## API Endpoints

- `POST /search` - Search for similar product images using vector similarity
- `GET /stats` - Get statistics about the vector index
- `GET /health` - Health check endpoint

## Event Handling

The service subscribes to `features.ready` events and automatically indexes embeddings for product images.

## Running Tests

```bash
python -m pytest tests/ -v
```