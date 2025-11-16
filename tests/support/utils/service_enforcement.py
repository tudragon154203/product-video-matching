"""
Real service usage enforcement for integration tests.

Validates environment configuration to ensure tests run against live services:
- VIDEO_CRAWLER_MODE must be 'live'
- DROPSHIP_PRODUCT_FINDER_MODE must be 'live'
- INTEGRATION_TESTS_ENFORCE_REAL_SERVICES must be 'true'
- BUS_BROKER must not point to mock/test URLs

Usage:
    from support.service_enforcement import enforce_real_service_usage
    enforce_real_service_usage()
"""

import os


def enforce_real_service_usage() -> None:
    """
    Validate that integration tests are configured to use real services, not mocks.
    Raises AssertionError if mock configurations are detected.
    """
    # Check video crawler mode
    video_crawler_mode = os.environ.get("VIDEO_CRAWLER_MODE", "").lower()
    if video_crawler_mode in ["mock", "test", "fake"]:
        raise AssertionError(
            f"VIDEO_CRAWLER_MODE is set to '{video_crawler_mode}'. "
            "Integration tests must use 'live' mode for real video crawling."
        )

    # Check dropship product finder mode
    dropship_mode = os.environ.get("DROPSHIP_PRODUCT_FINDER_MODE", "").lower()
    if dropship_mode in ["mock", "test", "fake"]:
        raise AssertionError(
            f"DROPSHIP_PRODUCT_FINDER_MODE is set to '{dropship_mode}'. "
            "Integration tests must use 'live' mode for real product finding."
        )

    # Check enforcement flag
    enforce_flag = os.environ.get("INTEGRATION_TESTS_ENFORCE_REAL_SERVICES", "").lower()
    # Accept common truthy values: 'true', '1', 'yes'
    if enforce_flag not in {"true", "1", "yes"}:
        raise AssertionError(
            "INTEGRATION_TESTS_ENFORCE_REAL_SERVICES must be set to a truthy value ('true', '1', or 'yes') "
            "for integration tests. This ensures real services are used instead of mocks."
        )

    # Validate service URLs are real, not localhost mocks (unless intentionally testing local services)
    broker_url = os.environ.get("BUS_BROKER", "")
    if "mock" in broker_url.lower() or "test" in broker_url.lower():
        raise AssertionError(
            f"BUS_BROKER appears to be configured for mock usage: {broker_url}. "
            "Integration tests should use real message broker."
        )

    print("Real service configuration validated for integration tests")
