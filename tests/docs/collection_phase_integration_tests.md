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

#### Option 1: Direct Pytest Execution (Recommended)
```bash
# Run all collection phase tests
pytest -m "collection_phase" -v

# Run specific minimal test
pytest tests/integration/test_collection_phase_happy_path.py::TestCollectionPhaseHappyPath::test_collection_phase_happy_path_minimal_dataset -v --no-cov -s

# Run comprehensive validation test
pytest tests/integration/test_collection_phase_happy_path.py::TestCollectionPhaseHappyPath::test_collection_phase_comprehensive_validation -v --no-cov -s

# Run idempotency test
pytest tests/integration/test_collection_phase_happy_path.py::TestCollectionPhaseHappyPath::test_collection_phase_idempotency_validation -v --no-cov -s
```

#### Option 2: Test Execution with Coverage
```bash
# Run with coverage report
pytest -m "collection_phase" -v --cov=tests --cov-report=html:htmlcov --cov-report=term

# Run specific test with coverage
pytest tests/integration/test_collection_phase_happy_path.py::TestCollectionPhaseHappyPath::test_collection_phase_happy_path_minimal_dataset -v --cov=tests --cov-report=term
```

## Test Scenarios

### 1. Minimal Dataset Scenario
- **Purpose**: Validate basic collection workflow
- **Duration**: ~25-30 seconds
- **Data**: 1-3 products, 2-5 videos
- **Validation**: Event flow, database state, observability, correlation ID propagation
- **Command**: `pytest tests/integration/test_collection_phase_happy_path.py::TestCollectionPhaseHappyPath::test_collection_phase_happy_path_minimal_dataset -v`

### 2. Comprehensive Scenario
- **Purpose**: Validate complete workflow with full data set
- **Duration**: ~1-2 minutes
- **Data**: Multiple products, videos, platforms
- **Validation**: All aspects of collection workflow
- **Command**: `pytest tests/integration/test_collection_phase_happy_path.py::TestCollectionPhaseHappyPath::test_collection_phase_comprehensive_validation -v`

### 3. Idempotency Validation
- **Purpose**: Ensure duplicate requests don't create duplicate data
- **Duration**: ~30-45 seconds
- **Validation**: Event ledger tracking, database state, correlation ID consistency
- **Command**: `pytest tests/integration/test_collection_phase_happy_path.py::TestCollectionPhaseHappyPath::test_collection_phase_idempotency_validation -v`

### 4. All Collection Phase Tests
- **Purpose**: Run complete test suite for collection phase
- **Duration**: ~2-3 minutes total
- **Validation**: Full coverage of collection workflow
- **Command**: `pytest -m "collection_phase" -v`

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
from tests.support.message_spy import CollectionPhaseSpy

async with CollectionPhaseSpy(broker_url) as spy:
    # Spy queues are automatically set up for:
    # - products.collections.completed
    # - videos.collections.completed
    
    # Wait for events
    products_event = await spy.wait_for_products_completed(job_id, timeout=30.0)
    videos_event = await spy.wait_for_videos_completed(job_id, timeout=300.0)
```

### 2. Database Cleanup ([`utils/db_cleanup.py`](./utils/db_cleanup.py))

Provides database cleanup and validation:

```python
from tests.support.db_cleanup import CollectionPhaseCleanup, DatabaseStateValidator

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
from tests.support.event_publisher import CollectionEventPublisher, TestEventFactory

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
from tests.support.test_environment import CollectionPhaseTestEnvironment

async with CollectionPhaseTestEnvironment(db_manager, message_broker, broker_url) as env:
    # Environment is automatically set up with:
    # - Test job record
    # - Spy queues
    # - Clean database state
    
    # Publish collection requests
    await env.publish_collection_requests(
        products_queries=["test product"],
        videos_queries={"vi": ["test video"], "zh": ["测试视频"]},
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
- **Products completion**: Default timeout is 30 seconds
- **Videos completion**: Default timeout is 300 seconds (5 minutes) to accommodate YouTube crawling
- Check service logs for processing bottlenecks
- Verify system resources (CPU, memory)
- For slow systems, consider increasing timeout values further

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
python tests/scripts/run_collection_phase_tests.py --test-type ci

# Run with CI environment variables
ENVIRONMENT=ci python tests/scripts/run_collection_phase_tests.py --test-type ci
```

## Recent Updates (October 16, 2025)

### Key Improvements Made

1. **Correlation ID Propagation**: Successfully implemented end-to-end correlation ID tracking across all services
2. **Timeout Optimization**: Updated timeout values to reflect real-world processing times:
   - Products completion: 30 seconds (was 10 seconds)
   - Videos completion: 300 seconds (was 10 seconds)
3. **Product Model Enhancement**: Added missing `job_id` field to Product model and updated CRUD operations
4. **Database Schema Alignment**: Fixed job creation to use correct schema (removed deprecated `status` field)
5. **Test Infrastructure**: Improved message spy API compatibility and test reliability
6. **Video Collection**: Updated expectations to collect "at least 2 videos" instead of "maximum 2 videos"

### Current Test Performance

- **Minimal Dataset Test**: ~25 seconds (previously estimated 5 minutes)
- **Real Video Crawling**: Successfully integrates with YouTube API for actual video collection
- **Products Collection**: Rapid completion within seconds
- **End-to-End Validation**: Complete workflow validation with correlation tracking

### Known Working Commands

```bash
# Run the main happy path test (currently passing)
pytest tests/integration/test_collection_phase_happy_path.py::TestCollectionPhaseHappyPath::test_collection_phase_happy_path_minimal_dataset -v --no-cov -s

# Run all collection phase tests
pytest -m "collection_phase" -v
```

---

**Document Version**: 1.1
**Last Updated**: October 16, 2025
**Maintainer**: Development Team