# eBay Collector Integration Tests

This directory contains integration tests for the eBay product collector that use real eBay API calls.

## Overview

The integration tests in this directory test the complete flow from eBay OAuth 2.0 authentication to product collection using real eBay Browse API calls. These tests validate:

- eBay OAuth 2.0 authentication and token management
- Real product collection from eBay API
- Data validation and integrity
- Error handling and edge cases
- Performance metrics
- Concurrent collection capabilities

## Test Files

- `test_ebay_collector_real2.py` - Main integration test file with comprehensive test cases
- `test.env` - Test configuration template
- `__init__.py` - Makes the directory a Python package

## Prerequisites

### 1. eBay API Credentials

You need eBay API credentials to run these tests. Get them from the [eBay Developer Portal](https://developer.ebay.com/):

1. Create a sandbox application
2. Note your `App ID` and `Cert ID` (Client Secret)
3. Ensure you have the necessary OAuth scopes

### 2. Environment Configuration

Copy `test.env` to `.env` in the same directory and fill in your credentials:

```bash
cp test.env .env
```

Edit `.env` with your actual values:

```env
# eBay API Configuration (required for real API tests)
EBAY_CLIENT_ID=your_sandbox_app_id_here
EBAY_CLIENT_SECRET=your_sandbox_app_secret_here
EBAY_MARKETPLACES=EBAY_US
EBAY_ENVIRONMENT=sandbox
EBAY_SCOPES="https://api.ebay.com/oauth/api_scope"

# Mock Configuration
USE_MOCK_FINDERS=false

# Redis Configuration (for token storage)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
```

### 3. Required Services

- **Redis Server**: For token storage (required for authentication)
- **Python Dependencies**: Install with `pip install pytest pytest-asyncio httpx requests aioredis python-dotenv`

## Running Tests

### Individual Test Functions

Run specific test functions:

```bash
# Run authentication test
python -m pytest test_ebay_collector_real2.py::test_authentication_flow -v

# Run basic collection test
python -m pytest test_ebay_collector_real2.py::test_basic_product_collection -v

# Run data validation test
python -m pytest test_ebay_collector_real2.py::test_data_validation -v
```

### All Tests

Run all integration tests:

```bash
python -m pytest test_ebay_collector_real2.py -v
```

### Comprehensive Test

Run the comprehensive test with detailed reporting:

```bash
python test_ebay_collector_real2.py
```

This will generate a detailed JSON report with test results.

### Test Categories

The tests are organized into several categories:

1. **Authentication Tests**
   - `test_authentication_flow`: Tests OAuth 2.0 authentication
   - `test_token_refresh`: Tests token refresh functionality

2. **Collection Tests**
   - `test_basic_product_collection`: Tests basic product collection
   - `test_multiple_queries`: Tests collection with multiple queries
   - `test_deduplication_logic`: Tests product deduplication
   - `test_concurrent_collection`: Tests concurrent collection

3. **Data Validation Tests**
   - `test_data_validation`: Tests data integrity and validation
   - `test_image_handling`: Tests image processing
   - `test_shipping_cost_calculation`: Tests shipping cost logic

4. **Error Handling Tests**
   - `test_error_handling`: Tests edge cases and error scenarios

5. **Performance Tests**
   - `test_performance_metrics`: Tests collection performance

6. **Configuration Tests**
   - `test_source_name`: Tests source name functionality
   - `test_marketplace_configuration`: Tests marketplace configuration

## Test Configuration

### Environment Variables

The tests use the following environment variables:

- `EBAY_CLIENT_ID`: eBay App ID
- `EBAY_CLIENT_SECRET`: eBay Client Secret
- `EBAY_MARKETPLACES`: Comma-separated list of marketplaces (e.g., "EBAY_US,EBAY_UK")
- `EBAY_ENVIRONMENT`: "sandbox" or "production"
- `REDIS_HOST`: Redis server host
- `REDIS_PORT`: Redis server port
- `REDIS_PASSWORD`: Redis password (if any)
- `REDIS_DB`: Redis database number

### Test Data

Tests use real eBay search queries like:
- "iphone", "laptop", "headphones", "watch", "shoes"
- "camera", "electronics", "tablet", "phone"

These queries are chosen because they typically return good results in eBay's sandbox environment.

## Expected Results

### Successful Test Run

A successful test run should show:

- ✅ Authentication successful with valid token
- ✅ Product collection returning expected number of results
- ✅ Data validation passing for all products
- ✅ Performance metrics within acceptable ranges
- ✅ Error handling working correctly

### Common Issues

1. **Authentication Failures**
   - Check eBay credentials in `.env` file
   - Ensure eBay sandbox application is properly configured
   - Verify network connectivity to eBay API

2. **Redis Connection Issues**
   - Ensure Redis server is running
   - Check Redis connection parameters
   - Verify Redis has enough memory for token storage

3. **Rate Limiting**
   - eBay API has rate limits
   - Tests include delays to avoid rate limiting
   - If you hit rate limits, wait a few minutes before retrying

4. **Empty Results**
   - Some queries may return no results in sandbox
   - Try different search terms
   - Verify marketplace configuration

## Test Output

### JSON Reports

When running the comprehensive test (`python test_ebay_collector_real2.py`), a JSON report is generated with:

- Test execution timestamp
- Configuration details
- Individual test results
- Performance metrics
- Summary statistics

### Log Output

Tests provide detailed logging output including:

- Authentication status and token details
- Product collection statistics
- Performance metrics
- Error details when tests fail

## Best Practices

1. **Run Tests in Sandbox**: Always use eBay's sandbox environment for testing
2. **Monitor Rate Limits**: Be aware of eBay API rate limits
3. **Check Credentials**: Verify eBay credentials before running tests
4. **Review Logs**: Check test logs for detailed information
5. **Clean Up**: Redis tokens are automatically cleaned up after tests

## Continuous Integration

These integration tests can be integrated into CI/CD pipelines. Ensure:

1. eBay credentials are stored securely as environment variables
2. Redis service is available in the CI environment
3. Network access to eBay API is permitted
4. Test execution time is monitored (tests may take 1-3 minutes)

## Troubleshooting

### Common Error Messages

- `Failed to obtain eBay access token`: Check eBay credentials and network connectivity
- `Redis connection failed`: Ensure Redis server is running and accessible
- `Rate limit exceeded`: Wait before retrying or reduce test frequency
- `No products found`: Try different search queries or check marketplace configuration

### Debug Mode

Enable debug logging by setting `LOG_LEVEL=DEBUG` in your environment:

```env
LOG_LEVEL=DEBUG
```

This will provide more detailed information about test execution.