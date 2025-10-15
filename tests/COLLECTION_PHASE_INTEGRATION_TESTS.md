# Collection Phase Integration Tests Guide

This guide provides comprehensive documentation for running and understanding the Collection Phase Integration Tests, which validate the complete workflow from publishing collection requests to verifying completion events and database state.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Test Execution](#test-execution)
4. [Test Scenarios](#test-scenarios)
5. [Infrastructure Setup](#infrastructure-setup)
6. [Mock Data Usage](#mock-data-usage)
7. [Test Components](#test-components)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

## Overview

The Collection Phase Integration Tests validate the end-to-end collection workflow according to Sprint 13.1 PRD specifications. The tests ensure that:

- Collection requests are properly processed
- Completion events are generated within timeout constraints
- Data is correctly persisted to the database
- Idempotency is maintained (no duplicate processing)
- Observability requirements are met (logging, metrics, correlation IDs)

### Key Test Components

- **Message Spy**: Ephemeral RabbitMQ queues for event interception
- **Database Cleanup**: Automated cleanup with test isolation
- **Event Publisher**: Utilities for publishing test events
- **Test Environment**: Complete environment setup and teardown
- **Mock Data**: Synthetic test data with deterministic IDs

## Quick Start

### Prerequisites

1. Start the development stack:
   ```bash
   docker compose -f infra/pvm/docker-compose.dev.cpu.yml up -d
   ```

2. Run database migrations:
   ```bash
   python scripts/run_migrations.py upgrade
   ```

3. Install test dependencies:
   ```bash
   pip install -r requirements-test.txt
   ```

4. Configure environment:
   ```bash
   cp infra/pvm/.env.example infra/pvm/.env
   ```

### Running Tests

#### Option 1: Simple Test Runner (Recommended for daily development)
```bash
# Run collection phase tests only
python tests/run_collection_phase_tests.py

# Run with verbose output
python tests/run_collection_phase_tests.py --verbose
```

#### Option 2: Comprehensive Test Runner
```bash
# Run minimal scenario
python tests/run_collection_phase_tests.py --scenario minimal

# Run comprehensive scenario
python tests/run_collection_phase_tests.py --scenario comprehensive

# Run idempotency tests
python tests/run_collection_phase_tests.py --scenario idempotency

# Run observability tests
python tests/run_collection_phase_tests.py --scenario observability
```

#### Option 3: Direct Pytest Execution
```bash
# Run all collection phase tests
pytest -m "collection_phase" -v

# Run specific test
pytest tests/integration/test_collection_phase_happy_path.py::TestCollectionPhaseHappyPath::test_collection_phase_happy_path_minimal_dataset -v
```

## Test Scenarios

### 1. Minimal Dataset Scenario
- **Purpose**: Validate basic collection workflow
- **Duration**: ~5 minutes
- **Data**: 1-2 products, 1-2 videos
- **Validation**: Event flow, database state, observability
- **Command**: `python tests/run_collection_phase_tests.py --scenario minimal`

### 2. Comprehensive Scenario
- **Purpose**: Validate complete workflow with full data set
- **Duration**: ~10-15 minutes
- **Data**: Multiple products, videos, platforms
- **Validation**: All aspects of collection workflow
- **Command**: `python tests/run_collection_phase_tests.py --scenario comprehensive`

### 3. Idempotency Validation
- **Purpose**: Ensure duplicate requests don't create duplicate data
- **Duration**: ~8 minutes
- **Validation**: Event ledger tracking, database state
- **Command**: `python tests/run_collection_phase_tests.py --scenario idempotency`

### 4. Observability Validation
- **Purpose**: Validate logging, metrics, and health checks
- **Duration**: ~6 minutes
- **Validation**: Correlation ID tracking, service logs
- **Command**: `python tests/run_collection_phase_tests.py --scenario observability`

## Infrastructure Setup

### Test Configuration

The tests use pytest configuration defined in [`pytest.ini`](../pytest.ini):

```ini
[pytest]
asyncio_mode = auto
addopts = --doctest-modules --strict-markers -n auto --cov=tests --cov-report=term-missing --cov-report=html:htmlcov --cov-report=xml
norecursedirs = .git .pytest_cache .tox venv *.egg dist build model_cache
timeout = 300
timeout_method = thread
```

### Test Markers

Tests are categorized using pytest markers:

- `@pytest.mark.collection_phase`: Collection phase integration tests
- `@pytest.mark.integration`: General integration tests
- `@pytest.mark.observability`: Observability validation tests
- `@pytest.mark.performance`: Performance benchmark tests
- `@pytest.mark.idempotency`: Idempotency validation tests
- `@pytest.mark.ci`: Tests suitable for CI environment
- `@pytest.mark.slow`: Long-running tests

### Environment Variables

Key environment variables for test execution:

```bash
POSTGRES_DSN=postgresql://postgres:postgres@localhost:5432/test_db
BUS_BROKER=amqp://guest:guest@localhost:5672/
REDIS_URL=redis://localhost:6379
ENVIRONMENT=local
LOG_LEVEL=INFO
```

## Mock Data Usage

### Mock Data Structure

The tests use synthetic test data located in [`mock_data/`](./mock_data/):

```
tests/mock_data/
├── products/                    # Product mock data
│   ├── products_collect_request.json
│   ├── products_collections_completed.json
│   ├── product_001.json
│   ├── product_002.json
│   └── product_003.json
├── videos/                      # Video mock data
│   ├── videos_search_request.json
│   ├── videos_collections_completed.json
│   ├── video_001.json
│   ├── video_002.json
│   ├── video_001_keyframes.json
│   └── video_002_keyframes.json
└── fixtures/                    # Fixture loader utilities
    ├── __init__.py
    └── test_fixtures.py
```

### Using Mock Data

```python
from tests.mock_data.fixtures import MockDataLoader

# Get products collect request
request = MockDataLoader.get_products_collect_request()

# Get all products
products = MockDataLoader.get_all_products()

# Get specific product
product = MockDataLoader.get_product(1)

# Get videos search request
request = MockDataLoader.get_videos_search_request()

# Generate deterministic test IDs
job_id = MockDataLoader.generate_test_job_id("integration_test")
event_id = MockDataLoader.generate_test_event_id()
```

### Key Features

- **No External Dependencies**: All data is self-contained
- **Deterministic**: Same IDs and data across test runs
- **Schema Compliant**: Validated against contract schemas
- **Minimal**: Small, realistic datasets for fast test execution

## Test Components

### 1. Message Spy ([`utils/message_spy.py`](./utils/message_spy.py))

Provides RabbitMQ message spying capabilities:

```python
from tests.utils.message_spy import CollectionPhaseSpy

async with CollectionPhaseSpy(broker_url) as spy:
    # Spy queues are automatically set up for:
    # - products.collections.completed
    # - videos.collections.completed
    
    # Wait for events
    products_event = await spy.wait_for_products_completed(job_id, timeout=10.0)
    videos_event = await spy.wait_for_videos_completed(job_id, timeout=10.0)
```

### 2. Database Cleanup ([`utils/db_cleanup.py`](./utils/db_cleanup.py))

Provides database cleanup and validation:

```python
from tests.utils.db_cleanup import CollectionPhaseCleanup, DatabaseStateValidator

cleanup = CollectionPhaseCleanup(db_manager)
validator = DatabaseStateValidator(db_manager)

# Clean up test data
await cleanup.cleanup_test_data("test_%")

# Validate database state
await validator.assert_products_collected(job_id, min_count=1)
await validator.assert_videos_collected(job_id, min_count=1)
```

### 3. Event Publisher ([`utils/event_publisher.py`](./utils/event_publisher.py))

Provides event publishing utilities:

```python
from tests.utils.event_publisher import CollectionEventPublisher, TestEventFactory

publisher = CollectionEventPublisher(message_broker)
factory = TestEventFactory()

# Publish collection requests
correlation_id = await publisher.publish_products_collect_request(
    job_id=job_id,
    queries={"en": ["ergonomic pillows"]},
    top_amz=20,
    top_ebay=20
)
```

### 4. Test Environment ([`utils/test_environment.py`](./utils/test_environment.py))

Provides complete test environment management:

```python
from tests.utils.test_environment import CollectionPhaseTestEnvironment

async with CollectionPhaseTestEnvironment(db_manager, message_broker, broker_url) as env:
    # Environment is automatically set up with:
    # - Test job record
    # - Spy queues
    # - Clean database state
    
    # Publish collection requests
    await env.publish_collection_requests(
        products_queries=["test product"],
        videos_queries={"vi": ["test video"]},
        industry="test industry",
        platforms=["youtube"]
    )
    
    # Wait for completion
    completion = await env.wait_for_collection_completion()
```

## Troubleshooting

### Common Issues

#### Docker Compose Issues
```bash
# Check if services are running
docker compose -f infra/pvm/docker-compose.dev.cpu.yml ps

# Check service logs
docker compose -f infra/pvm/docker-compose.dev.cpu.yml logs -f <service>

# Restart services
docker compose -f infra/pvm/docker-compose.dev.cpu.yml restart
```

#### Database Connection Issues
```bash
# Check database connectivity
python -c "import asyncpg; asyncio.run(asyncpg.connect('postgresql://postgres:postgres@localhost:5432/test_db'))"

# Re-run migrations
python scripts/run_migrations.py upgrade
```

#### Message Broker Issues
```bash
# Check RabbitMQ status
docker compose -f infra/pvm/docker-compose.dev.cpu.yml logs rabbitmq

# Check broker connectivity
python -c "import aio_pika; asyncio.run(aio_pika.connect('amqp://guest:guest@localhost:5672/'))"
```

#### Test Timeout Issues
- Increase timeout values in test configuration
- Check service logs for processing bottlenecks
- Verify system resources (CPU, memory)

#### Test Isolation Issues
- Verify cleanup is working properly
- Check for test data leakage between tests
- Ensure unique job IDs for each test

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Enable debug logging
LOG_LEVEL=DEBUG pytest tests/integration/test_collection_phase_happy_path.py -v -s

# Run with maximum verbosity
pytest tests/integration/test_collection_phase_happy_path.py -vv -s --tb=long
```

### Manual Cleanup

If automatic cleanup fails, manual cleanup may be required:

```sql
-- Clean up test jobs
DELETE FROM matches WHERE job_id LIKE 'test_%';
DELETE FROM video_frames WHERE video_id IN (SELECT video_id FROM videos WHERE job_id LIKE 'test_%');
DELETE FROM product_images WHERE product_id IN (SELECT product_id FROM products WHERE job_id LIKE 'test_%');
DELETE FROM videos WHERE job_id LIKE 'test_%';
DELETE FROM products WHERE job_id LIKE 'test_%';
DELETE FROM jobs WHERE job_id LIKE 'test_%';
```

## Best Practices

### Test Development

1. **Use descriptive test names**: Clearly indicate what is being tested
2. **Add appropriate markers**: Use pytest markers for categorization
3. **Include timeout values**: Set reasonable timeouts for each test
4. **Validate contracts**: Ensure events conform to schemas
5. **Check database state**: Verify data persistence and integrity

### Test Execution

1. **Run prerequisites first**: Ensure infrastructure is running
2. **Use appropriate scenarios**: Choose minimal for quick validation
3. **Monitor resource usage**: Check system resources during execution
4. **Review test logs**: Check for warnings and errors
5. **Validate cleanup**: Ensure no test data leakage

### Maintenance

1. **Update test data**: Keep test data realistic and relevant
2. **Review timeout values**: Adjust based on system performance
3. **Monitor test duration**: Identify slow tests for optimization
4. **Update documentation**: Keep this guide current with changes
5. **Regular cleanup**: Remove old test data and logs

## Performance Considerations

### Optimization Features

- **Parallel Execution**: Automatic test parallelization with `-n auto`
- **CPU-optimized Infrastructure**: Use `docker-compose.dev.cpu.yml`
- **Aggressive Teardown**: Cost minimization per PRD requirements
- **Test Isolation**: Proper cleanup and isolation between tests

### Resource Requirements

- **Minimum**: 4GB RAM, 2 CPU cores
- **Recommended**: 8GB RAM, 4 CPU cores
- **Storage**: 10GB free space for test data and logs

## Test Results and Reporting

### Report Types

- **JSON Report**: `test_report.json` - Detailed test results
- **Coverage Report**: `htmlcov/index.html` - HTML coverage report
- **XML Report**: `pytest.xml` - JUnit-compatible XML report
- **Execution Log**: `test_execution.log` - Detailed execution log

### Coverage Analysis

Generate coverage reports:

```bash
# Generate HTML coverage report
pytest --cov=tests --cov-report=html tests/integration/

# Generate terminal coverage summary
pytest --cov=tests --cov-report=term-missing tests/integration/

# Generate XML coverage for CI
pytest --cov=tests --cov-report=xml tests/integration/
```

## CI/CD Integration

The tests are integrated with GitHub Actions through `.github/workflows/ci-collection-phase.yml`. The workflow includes:

- **Prerequisites validation**: Environment setup verification
- **Test execution**: Multiple scenarios and configurations
- **Security checks**: Bandit, safety, and code quality
- **Performance benchmarks**: Optional performance testing
- **Reporting**: Test results, coverage, and artifacts

### Local CI Simulation

Simulate CI environment locally:

```bash
# Run CI-optimized tests
python tests/run_collection_phase_tests.py --test-type ci

# Run with CI environment variables
ENVIRONMENT=ci python tests/run_collection_phase_tests.py --test-type ci
```

---

**Document Version**: 1.0  
**Last Updated**: October 15, 2025  
**Maintainer**: Development Team