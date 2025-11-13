# Integration Tests

This directory contains integration tests for the `dropship-product-finder` microservice. These tests verify the interactions between different components and external services (e.g., databases, other microservices) within a near-production environment.

Each test module directly under this directory should be named descriptively (e.g., `test_feature_name.py`) and should include `pytestmark = pytest.mark.integration` to ensure proper test filtering.

## External dependencies

The eBay collector suites (`test_ebay_collector_*.py`, `test_e2e_auth.py`) now exercise the real eBay Browse and OAuth APIs. Before running them you must export valid eBay credentials (client ID, client secret, redirect URI, etc.) so that the `config_loader` can build the production or sandbox configuration. Without real credentials the requests will fail with authentication errors.

Be mindful of rate limits when running the tests repeatedly—the suites intentionally avoid stubbing the Browse API so they can verify end-to-end payloads, which means every run consumes real API calls.
