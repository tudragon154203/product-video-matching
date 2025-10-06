#!/usr/bin/env python3
"""Integration tests for EbayApiClient using eBay production credentials."""

import sys
from pathlib import Path
from typing import Dict, Iterable, List

import pytest

from collectors.ebay.ebay_api_client import EbayApiClient
from config_loader import config
from services.auth import eBayAuthService
from services.ebay_browse_api_client import EbayBrowseApiClient

# Add current directory to Python path so service modules resolve when the test runs directly
sys.path.insert(0, str(Path(__file__).parent.parent))


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def event_loop():
    """Create a fresh asyncio loop for this test module."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def auth_service(redis_client):
    """Return a production-configured eBay auth service."""
    if not config.EBAY_PRODUCTION_CLIENT_ID or not config.EBAY_PRODUCTION_CLIENT_SECRET:
        pytest.skip("Production credentials are not configured")

    config.EBAY_ENVIRONMENT = "production"

    service = eBayAuthService(config, redis_client)
    yield service
    await service.close()


@pytest.fixture(scope="module")
async def ebay_browse_client(auth_service):
    """Instantiate the browse client bound to the production marketplace."""
    client = EbayBrowseApiClient(
        auth_service=auth_service,
        marketplace_id="EBAY_US",
        base_url=config.EBAY_BROWSE_BASE,
    )
    yield client


@pytest.fixture(scope="module")
def ebay_api_client(ebay_browse_client):
    """Expose the EbayApiClient under test."""
    return EbayApiClient(ebay_browse_client)


def _extract_image_urls(item: Dict[str, object]) -> List[str]:
    """Pull image URLs from the different structures eBay may return."""
    urls: List[str] = []

    image = item.get("image")
    if isinstance(image, dict):
        primary = image.get("imageUrl")
        if isinstance(primary, str) and primary:
            urls.append(primary)

    gallery_info = item.get("galleryInfo")
    if isinstance(gallery_info, dict):
        variations = gallery_info.get("imageVariations", [])
        if isinstance(variations, Iterable):
            for variation in variations:
                if isinstance(variation, dict):
                    alt = variation.get("imageUrl")
                    if isinstance(alt, str) and alt:
                        urls.append(alt)

    images = item.get("images")
    if isinstance(images, Iterable):
        for entry in images:
            if isinstance(entry, dict):
                extra = entry.get("imageUrl") or entry.get("imageUrlHd")
                if isinstance(extra, str) and extra:
                    urls.append(extra)

    return list(dict.fromkeys(urls))


@pytest.mark.asyncio
async def test_fetch_details_returns_multiple_images(ebay_api_client):
    """Fetch details via production and ensure at least two image URLs are present."""
    query = "phone"
    limit = 5
    top_k = 3

    summaries, item_details = await ebay_api_client.fetch_and_get_details(
        query=query,
        limit=limit,
        offset=0,
        marketplace="EBAY_US",
        top_k=top_k,
    )

    assert summaries, "Expected at least one item summary from the search"
    assert item_details, "Expected detailed responses for the fetched items"

    total_images = 0

    for detail in item_details:
        item = detail.get("item", detail)
        if not isinstance(item, dict):
            continue

        image_urls = _extract_image_urls(item)
        total_images += len(image_urls)

    assert (
        total_images >= 2
    ), f"Expected at least two image URLs, got {total_images}"
