#!/usr/bin/env python3
"""
Integration tests for eBay Browse API focusing on sandbox behavior.
Tests the search and get_item endpoints with real eBay API calls.
"""

import os
import pytest
import sys
from pathlib import Path
from typing import Dict, Any

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ebay_browse_api_client import EbayBrowseApiClient
from services.auth import eBayAuthService
from config_loader import config

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for each test module"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def auth_service(redis_client):
    """eBay authentication service fixture for sandbox environment"""
    # Force sandbox environment for this test
    config.EBAY_ENVIRONMENT = "sandbox"
    
    service = eBayAuthService(config, redis_client)
    yield service
    await service.close()


@pytest.fixture(scope="module")
async def ebay_browse_client(auth_service):
    """eBay Browse API client fixture"""
    client = EbayBrowseApiClient(
        auth_service=auth_service,
        marketplace_id="EBAY_US",
        base_url=config.EBAY_BROWSE_BASE,
    )
    yield client


@pytest.mark.asyncio
async def test_search_endpoint(ebay_browse_client):
    """Test the search endpoint with a known keyword"""
    # Perform search with "laptop" keyword
    result = await ebay_browse_client.search(q="laptop", limit=5)
    
    # Assert HTTP status code is 200 (implicit in successful response)
    assert isinstance(result, dict), "Search result should be a dictionary"
    
    # Assert response contains non-empty itemSummaries
    assert "itemSummaries" in result, "Response should contain itemSummaries"
    assert isinstance(result["itemSummaries"], list), "itemSummaries should be a list"
    assert len(result["itemSummaries"]) > 0, "Search should return at least one item"
    
    # Verify marketplace header by checking itemWebUrl contains expected domain
    first_item = result["itemSummaries"][0]
    assert "itemWebUrl" in first_item, "First item should have itemWebUrl"
    item_web_url = first_item["itemWebUrl"]
    assert isinstance(item_web_url, str), "itemWebUrl should be a string"
    assert ".ebay.com" in item_web_url, f"itemWebUrl should contain '.ebay.com': {item_web_url}"
    
    # Log successful search
    print(f"Successfully found {len(result['itemSummaries'])} items for 'laptop'")


@pytest.mark.asyncio
async def test_get_item_endpoint(ebay_browse_client):
    """Test the get_item endpoint using an ID from search results"""
    # First, get an item ID from a successful search
    search_result = await ebay_browse_client.search(q="laptop", limit=5)
    assert "itemSummaries" in search_result and len(search_result["itemSummaries"]) > 0, \
        "Search should return items to get an ID from"

    # Get the first item ID
    item_id = search_result["itemSummaries"][0]["itemId"]
    assert isinstance(item_id, str), "Item ID should be a string"
    assert len(item_id) > 0, "Item ID should not be empty"

    # Call get_item with this ID
    item_result = await ebay_browse_client.get_item(item_id=item_id)

    # Assert HTTP status code is 200 (implicit in successful response)
    assert isinstance(item_result, dict), "Get item result should be a dictionary"
    
    # Handle case where item might not be found or API returns empty response
    if not item_result:
        pytest.skip("Item not found in get_item call (may be sandbox limitation)")
        return

    # Assert presence of key fields
    assert "title" in item_result, "Response should contain title"
    assert "price" in item_result, "Response should contain price"
    assert "image" in item_result, "Response should contain image"

    # Validate field types and basic structure
    assert isinstance(item_result["title"], str), "Title should be a string"
    assert len(item_result["title"].strip()) > 0, "Title should not be empty"

    # Price should be a valid price structure
    assert isinstance(item_result["price"], dict), "Price should be a dictionary"
    assert "value" in item_result["price"], "Price should have value field"
    assert "currency" in item_result["price"], "Price should have currency field"
    assert isinstance(item_result["price"]["value"], (int, float, str)), "Price value should be numeric or string"
    # Convert to float for numeric comparison
    price_value = float(item_result["price"]["value"])
    assert price_value > 0, "Price value should be positive"
    assert isinstance(item_result["price"]["currency"], str), "Price currency should be a string"

    # Image should be a valid image structure
    assert isinstance(item_result["image"], dict), "Image should be a dictionary"
    assert "imageUrl" in item_result["image"], "Image should have imageUrl field"
    assert isinstance(item_result["image"]["imageUrl"], str), "Image URL should be a string"
    assert item_result["image"]["imageUrl"].startswith(("http://", "https://")), \
        "Image URL should be a valid HTTP/HTTPS URL"

    # Log successful item retrieval
    print(f"Successfully retrieved item: {item_result['title'][:50]}... (ID: {item_id})")