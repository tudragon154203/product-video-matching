# Integration Tests - Real Service Enforcement

This directory contains integration tests that **ENFORCE** real service usage. No mocks are allowed in these tests.

## 🚫 NO MOCKS ALLOWED

These integration tests are designed to validate the complete system with real services:

- **dropship-product-finder**: Must be running in `live` mode
- **video-crawler**: Must be running in `live` mode
- **rabbitmq**: Real message broker required
- **postgresql**: Real database required
- **main-api**: Must be accessible for health checks

## Configuration Enforcement

### Environment Variables
The following environment variables are **ENFORCED** to prevent mock usage:

```bash
# Service Modes (must be 'live')
VIDEO_CRAWLER_MODE=live                    # ❌ mock/test/fake NOT allowed
DROPSHIP_PRODUCT_FINDER_MODE=live          # ❌ mock/test/fake NOT allowed

# Enforcement Flag
INTEGRATION_TESTS_ENFORCE_REAL_SERVICES=true  # ❌ false NOT allowed
```

### Validation Checks

1. **Startup Validation**: `conftest.py` validates real service configuration before any tests run
2. **Runtime Validation**: Each test method validates real service usage during execution
3. **Health Check Validation**: Tests verify services are actually responding (not just configured)

### Failure Scenarios

If mock configurations are detected, tests will **FAIL IMMEDIATELY**:

```
AssertionError: VIDEO_CRAWLER_MODE is set to 'mock'.
Integration tests must use 'live' mode for real video crawling.
```

## Running Integration Tests

### Prerequisites

1. **All services must be running**:
   ```bash
   ./up-dev.ps1  # Start all services
   ```

2. **Real API keys must be configured** (if services require them):
   - Amazon API keys for product scraping
   - eBay API keys for product scraping
   - YouTube API keys for video crawling

3. **Database must be accessible**:
   ```bash
   ./migrate.ps1  # Run migrations
   ```

### Execution

Note: Root-based pytest runs default to single worker (-n 1). You don't need to pass -n 1 explicitly.

```bash
# Run all integration tests from repo root
pytest -m integration -v

# Run collection phase tests from repo root
pytest -m "collection_phase" -v

# Optional coverage flags (not default)
pytest -m integration -v --cov=tests --cov-report=term-missing
```

### Configuration Files

- `pyproject.toml`: Root pytest configuration (strict markers, asyncio_mode=auto, import_mode=importlib, timeout=900, dotenv env_files)
- `infra/pvm/.env` and `tests/.env.test`: Environment files loaded via pytest-dotenv (override enabled)
- `conftest.py`: Validation logic for real services

## Test Validation

Each test performs the following validations:

### 1. Configuration Validation
```python
self.validate_real_service_usage()  # Checks env vars
```

### 2. Service Health Validation
```python
await self.validate_services_responding()  # Checks services are running
```

### 3. Real Data Validation
Tests verify that **real data** is collected from services:
- Products from Amazon/eBay with real ASINs/ItemIDs
- Videos from YouTube/TikTok with real video IDs
- Actual database records created by real services

## Debugging Real Service Issues

### Service Not Running
```
AssertionError: Cannot connect to Main API at http://localhost:8888.
Services may not be running.
```

**Solution**: Start services with `./up-dev.ps1`

### Mock Configuration Detected
```
AssertionError: VIDEO_CRAWLER_MODE must be 'live', got 'mock'
```

**Solution**: Ensure environment variables are set to `live` mode

### Service Health Check Failed
```
AssertionError: Main API health check failed: 503
```

**Solution**: Check service logs and ensure all dependencies are running

## Why Real Services Only?

1. **True Integration**: Validating actual service interactions, not mock simulations
2. **End-to-End Testing**: From API request → Real service processing → Database storage
3. **Production Confidence**: Tests exercise real code paths that will run in production
4. **API Contract Validation**: Real API responses validate service contracts
5. **Performance Characteristics**: Real service behavior includes actual network calls, processing times, and error handling

## Mock-Free Guarantee

This test suite guarantees that:

- ✅ No service responses are mocked
- ✅ No external APIs are stubbed
- ✅ No database interactions are faked
- ✅ All data comes from real service calls
- ✅ All failures come from real service behavior

Any attempt to use mocks will result in **immediate test failure**.