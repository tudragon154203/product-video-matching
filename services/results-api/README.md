# Results API Service

This service provides a REST API for accessing product-video matching results and related data.

## Architecture

The service follows a modular architecture with the following components:

1. **Main Entry Point** (`main.py`): Defines the FastAPI application and API endpoints.
2. **Configuration** (`config_loader.py`): Loads service configuration from environment variables.
3. **Business Logic** (`service.py`): Contains the main `ResultsService` class that implements the core functionality.
4. **Tests** (`tests/`): Unit tests for the service components.

## Key Features

- **Modular Design**: Separation of concerns with distinct modules for different responsibilities
- **FastAPI Framework**: High-performance REST API implementation
- **Dependency Injection**: Makes the service testable
- **Proper Error Handling**: Comprehensive error handling and logging
- **Resource Management**: Proper cleanup of resources on shutdown

## API Endpoints

- `GET /results` - List matching results with filtering and pagination
- `GET /products/{id}` - Get detailed product information
- `GET /videos/{id}` - Get detailed video information
- `GET /matches/{id}` - Get detailed match information
- `GET /evidence/{id}` - Serve evidence image for a match
- `GET /stats` - Get system statistics
- `GET /health` - Health check endpoint

## Running Tests

```bash
python -m pytest tests/ -v
```