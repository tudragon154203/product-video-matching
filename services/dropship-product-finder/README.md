# Dropship Product Finder Microservice

## Overview
This microservice is responsible for collecting product data from various e-commerce platforms. It is a key component of the Product-Video Matching System, designed to provide product information for matching with video content.

## Functionality
- Collects product data from various e-commerce platforms (e.g., eBay).
- Processes and normalizes product information.
- Publishes product data for further processing.

## In/Out Events
### Input Events
- `ProductCollectionRequest`: Request to initiate product data collection for a specific product or category.
  - Data: `{"source": "ebay", "query": "electronics"}`

### Output Events
- `ProductCollected`: Event indicating that product data has been successfully collected and processed.
  - Data: `{"product_id": "12345", "title": "Example Product", "image_url": "http://example.com/image.jpg"}`

## Current Progress
- Initial setup and basic eBay product collection implemented.
- Data normalization pipeline in progress.

## What's Next
- Integrate with additional e-commerce platforms (e.g., Amazon).
- Implement robust error handling and retry mechanisms.
- Optimize data collection performance.

## Testing

The dropship product finder service includes comprehensive unit and integration tests organized by category:

### Test Categories
- `unit`: Fast, isolated unit tests (default)
- `integration`: Integration tests with external dependencies (eBay APIs, Redis)
- `real_api`: Tests requiring live eBay API access (skipped by default)

### Running Tests

```bash
# Navigate to service directory first
cd services/dropship-product-finder

# Run only unit tests (fastest, recommended for development)
python -m pytest -m unit

# Run only integration tests
python -m pytest -m integration

# Run all tests (includes unit + integration)
python -m pytest tests/ -v

# Run with coverage
python -m pytest --cov=collectors --cov=services --cov=config_loader
```

### Test Organization
```
tests/
├── unit/                        # Unit tests (pytest.mark.unit)
│   ├── services/               # Service layer tests
│   │   ├── test_auth.py        # eBay authentication tests
│   │   ├── test_collectors.py  # Product collector tests
│   │   └── test_ebay_product_collector.py
│   └── utils/                  # Utility tests
│       └── test_config_loader.py
└── integration/                # Integration tests (pytest.mark.integration)
    ├── auth/                   # Authentication flow tests
    ├── test_e2e_auth.py        # End-to-end authentication
    └── test_parallelism_integration.py
```

### Key Test Areas
- **Authentication**: eBay OAuth token management and Redis caching
- **Product Collection**: eBay API integration, data normalization
- **Configuration**: Environment-based configuration validation
- **Parallelism**: Concurrent product collection across multiple sources