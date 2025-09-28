# Integration Tests

This directory contains integration tests for the `product-segmentor` microservice. These tests verify the interactions between different components and external services (e.g., databases, other microservices) within a near-production environment.

Each test module directly under this directory should be named descriptively (e.g., `test_feature_name.py`) and should include `pytestmark = pytest.mark.integration` to ensure proper test filtering.
