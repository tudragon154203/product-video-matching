#!/usr/bin/env python3
"""
Integration test for eBay product collector using production eBay API calls.
Tests the minimal essential flow from authentication to product collection with real data.
"""

from common_py.logging_config import configure_logging
import redis.asyncio as redis
from collectors.ebay_product_collector import EbayProductCollector
from services.auth import eBayAuthService
from config_loader import config
import asyncio
import pytest
import sys
from pathlib import Path
from datetime import datetime
import json

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


pytestmark = pytest.mark.integration


logger = configure_logging("dropship-product-finder:test_ebay_collector_production")


@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for each test module"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def redis_client():
    """Mock Redis client using dictionary storage"""

    class MockRedis:
        def __init__(self):
            self.data = {}

        async def setex(self, key, ttl, value):
            self.data[key] = value

        async def get(self, key):
            return self.data.get(key)

        async def close(self):
            pass

    return MockRedis()


@pytest.fixture(scope="module")
async def auth_service(redis_client):
    """eBay authentication service fixture"""
    # Force production environment for this test
    config.EBAY_ENVIRONMENT = "production"

    service = eBayAuthService(config, redis_client)
    yield service
    await service.close()


@pytest.fixture(scope="module")
async def ebay_collector(redis_client):
    """eBay product collector fixture"""
    collector = EbayProductCollector(
        data_root="/tmp/test_integration",
        redis_client=redis_client,
        marketplaces=["EBAY_US"],  # Test with US marketplace only
    )
    yield collector
    await collector.close()


@pytest.mark.asyncio
async def test_authentication_flow(auth_service):
    """Test eBay OAuth 2.0 authentication flow"""
    logger.info("Testing eBay authentication flow...")

    # Test token retrieval
    token = await auth_service.get_access_token()
    assert isinstance(token, str)
    assert len(token) > 0

    # Verify token is stored in Redis
    stored_token = await auth_service._retrieve_token()
    assert stored_token is not None
    assert "access_token" in stored_token
    assert "expires_in" in stored_token
    assert stored_token["expires_in"] > 0

    logger.info("Authentication successful, token length: %s", len(token))


@pytest.mark.asyncio
async def test_token_refresh(auth_service):
    """Test token refresh functionality"""
    logger.info("Testing token refresh...")

    # Get initial token
    initial_token = await auth_service.get_access_token()

    # Refresh token
    await auth_service._refresh_token()

    # Get new token
    new_token = await auth_service.get_access_token()

    # Verify token changed
    assert new_token != initial_token
    assert len(new_token) > 0

    logger.info("Token refresh successful")


@pytest.mark.asyncio
async def test_basic_product_collection(ebay_collector):
    """Test basic product collection with real eBay API"""
    logger.info("Testing basic product collection...")

    # Test with a common search query
    query = "iphone"
    top_k = 5

    products = await ebay_collector.collect_products(query, top_k)

    # Verify results
    assert isinstance(products, list)
    assert len(products) <= top_k  # Should not exceed requested limit

    # Verify product structure
    if products:
        product = products[0]
        assert "id" in product
        assert "title" in product
        assert "price" in product
        assert "currency" in product
        assert "url" in product
        assert "images" in product
        assert "marketplace" in product
        assert "totalPrice" in product
        assert "shippingCost" in product

        # Verify data types
        assert isinstance(product["title"], str)
        assert isinstance(product["price"], (int, float))
        assert isinstance(product["currency"], str)
        assert isinstance(product["images"], list)
        assert isinstance(product["marketplace"], str)
        assert isinstance(product["totalPrice"], (int, float))
        assert isinstance(product["shippingCost"], (int, float))

        # Verify marketplace is correct
        assert product["marketplace"] == "us"

        # Verify price is reasonable
        assert product["price"] > 0
        assert product["totalPrice"] >= product["price"]

        print("\n--- Sample Product Data (Production API) ---")
        print(json.dumps(product, indent=4))
        print("--------------------------------------------\n")

        logger.info("Collected %s products for '%s'", len(products), query)
        logger.info(
            "Sample product: %s... ($%s)",
            product["title"][:50],
            product["price"],
        )


@pytest.mark.asyncio
async def test_source_name(ebay_collector):
    """Test source name functionality"""
    source_name = ebay_collector.get_source_name()
    assert source_name == "ebay"
    logger.info("Source name: %s", source_name)