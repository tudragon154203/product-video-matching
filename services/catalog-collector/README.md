# Catalog Collector Service

This service is responsible for collecting product information from e-commerce platforms like Amazon and eBay.

## Architecture

The service follows a modular architecture with the following components:

1. **Main Entry Point** (`main.py`): Handles service initialization, event subscription, and graceful shutdown.
2. **Configuration** (`config_loader.py`): Loads service configuration from environment variables.
3. **Business Logic** (`service.py`): Contains the main `CatalogCollectorService` class that orchestrates product collection.
4. **Collectors** (`collectors.py`): Contains abstract base classes and implementations for different e-commerce platforms.
5. **Tests** (`tests/`): Unit tests for the service components.

## Key Features

- **Modular Design**: Easy to extend with new e-commerce platforms
- **Abstract Base Classes**: Ensures consistent interface for all collectors
- **Dependency Injection**: Makes the service testable
- **Proper Error Handling**: Comprehensive error handling and logging
- **Resource Management**: Proper cleanup of resources on shutdown

## Extending with New Platforms

To add support for a new e-commerce platform:

1. Create a new collector class that inherits from `BaseProductCollector`
2. Implement the required abstract methods:
   - `collect_products(self, query: str, top_k: int) -> List[Dict[str, Any]]`
   - `get_source_name(self) -> str`
3. Register the new collector in the `CatalogCollectorService.__init__` method

## Running Tests

```bash
python -m pytest tests/ -v
```