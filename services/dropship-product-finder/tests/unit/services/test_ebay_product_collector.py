"""
Unit tests for eBay Browse API client and eBay product collector.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from collectors.ebay.ebay_product_collector import EbayProductCollector
from services.ebay_browse_api_client import EbayBrowseApiClient

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_auth_service():
    """Mock authentication service"""
    auth = AsyncMock()
    auth.get_access_token = AsyncMock(return_value="test_token_123")
    auth.get_token = AsyncMock(
        return_value="test_token_123"
    )  # Keep for backwards compatibility
    auth.refresh_token = AsyncMock()
    auth._refresh_token = AsyncMock()
    auth._store_token = AsyncMock()
    auth._retrieve_token = AsyncMock(
        return_value={"access_token": "test_token_123", "expires_at": 9999999999}
    )
    auth._is_token_valid = AsyncMock(return_value=True)

    # Reset the mock to avoid state sharing between tests
    def reset_mock():
        auth.get_token.reset_mock()
        auth.refresh_token.reset_mock()
        auth.get_access_token.reset_mock()
        auth._refresh_token.reset_mock()
        auth._store_token.reset_mock()
        auth._retrieve_token.reset_mock()
        auth._is_token_valid.reset_mock()

    auth.reset_mock = reset_mock
    return auth


@pytest.fixture
def mock_ebay_auth_service():
    """Mock eBay auth service that doesn't fail with 401"""
    auth = AsyncMock()
    auth.get_access_token.return_value = "test_token_123"
    auth.get_token.return_value = "test_token_123"  # Keep for backwards compatibility
    auth.refresh_token = AsyncMock()
    auth._refresh_token = AsyncMock()
    auth._store_token = AsyncMock()
    auth._retrieve_token = AsyncMock(
        return_value={"access_token": "test_token_123", "expires_at": 9999999999}
    )
    auth._is_token_valid = AsyncMock(return_value=True)
    return auth


@pytest.fixture
def mock_config():
    """Mock configuration"""
    config = Mock()
    config.MAX_RETRIES_BROWSE = 3
    config.TIMEOUT_SECS_BROWSE = 30.0
    config.BACKOFF_BASE_BROWSE = 1.5
    return config


@pytest.fixture
def ebay_browse_client(mock_ebay_auth_service, mock_config):
    """Create eBay browse API client with mocked dependencies"""
    with patch("services.ebay_browse_api_client.config", mock_config):
        with patch("config_loader.config", mock_config):
            return EbayBrowseApiClient(
                auth_service=mock_ebay_auth_service,
                marketplace_id="EBAY_US",
                base_url="https://api.sandbox.ebay.com/buy/browse/v1",
            )


@pytest.fixture
def ebay_product_collector(mock_ebay_auth_service, mock_config):
    """Create eBay product collector with mocked auth service"""
    with patch("config_loader.config", mock_config):
        with patch("services.ebay_browse_api_client.config", mock_config):
            return EbayProductCollector(
                data_root="/tmp/test",
                redis_client=mock_ebay_auth_service,
                marketplaces=["EBAY_US", "EBAY_UK"],
            )


class TestEbayProductCollector:
    """Test cases for eBay product collector"""

    @pytest.mark.asyncio
    async def test_multiple_marketplaces(
        self, ebay_product_collector, mock_ebay_auth_service
    ):
        """Test collection from multiple marketplaces"""
        # Mock eBay browse API client for first marketplace
        mock_browse_client_us = AsyncMock()
        mock_browse_client_us.search.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "title": "US Product",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image1.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}],
                }
            ]
        }

        # Mock eBay browse API client for second marketplace
        mock_browse_client_uk = AsyncMock()
        mock_browse_client_uk.search.return_value = {
            "itemSummaries": [
                {
                    "itemId": "67890",
                    "title": "UK Product",
                    "price": {"value": 19.99, "currency": "GBP"},
                    "image": {"imageUrl": "https://example.com/image2.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}],
                }
            ]
        }

        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client_us,
            "EBAY_UK": mock_browse_client_uk,
        }

        # Collect products
        products = await ebay_product_collector.collect_products("test query", 2)

        # Verify both marketplaces were queried
        mock_browse_client_us.search.assert_called_once_with(
            q="test query", limit=2, offset=0
        )
        mock_browse_client_uk.search.assert_called_once_with(
            q="test query", limit=2, offset=0
        )

        # Verify products from both marketplaces
        assert len(products) == 2
        us_product = next(p for p in products if p["marketplace"] == "us")
        uk_product = next(p for p in products if p["marketplace"] == "uk")
        assert us_product["title"] == "US Product"
        assert uk_product["title"] == "UK Product"

    @pytest.mark.asyncio
    async def test_error_handling_during_collection(
        self, ebay_product_collector, mock_ebay_auth_service
    ):
        """Test error handling when one marketplace fails"""
        # Mock successful response for first marketplace
        mock_browse_client_us = AsyncMock()
        mock_browse_client_us.search.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "title": "US Product",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image1.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}],
                }
            ]
        }

        # Mock exception for second marketplace
        mock_browse_client_uk = AsyncMock()
        mock_browse_client_uk.search.side_effect = Exception("API Error")

        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client_us,
            "EBAY_UK": mock_browse_client_uk,
        }

        # Collect products - should not raise exception
        products = await ebay_product_collector.collect_products("test query", 2)

        # Verify successful product from first marketplace is returned
        assert len(products) == 1
        assert products[0]["title"] == "US Product"
        assert products[0]["marketplace"] == "us"

    @pytest.mark.asyncio
    async def test_pagination_handling(
        self, ebay_product_collector, mock_ebay_auth_service
    ):
        """Test pagination handling in product collection"""
        # Mock eBay browse API client with paginated response
        mock_browse_client = AsyncMock()
        mock_browse_client.search.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "title": "Product 1",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image1.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}],
                },
                {
                    "itemId": "67890",
                    "title": "Product 2",
                    "price": {"value": 19.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image2.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}],
                },
            ]
        }

        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client,  # Use same mock for both for simplicity
        }

        # Collect products with limit > 50 (should be clamped)
        products = await ebay_product_collector.collect_products("test query", 100)

        # Verify browse client was called with original limit.
        # Clamping happens inside the client implementation.
        assert mock_browse_client.search.call_count == 2
        for call in mock_browse_client.search.call_args_list:
            assert call.kwargs["limit"] == 100  # Original limit passed to search
            assert call.kwargs["offset"] == 0

        # Verify all products were collected
        assert len(products) == 2

    @pytest.mark.asyncio
    async def test_deduplication_by_epid(
        self, ebay_product_collector, mock_ebay_auth_service
    ):
        """Test deduplication by EPID with lowest price selection"""
        # Mock eBay browse API client with duplicate EPID
        mock_browse_client = AsyncMock()
        mock_browse_client.search.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "epid": "epid_001",
                    "title": "Higher Price Product",
                    "price": {"value": 35.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image1.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}],
                },
                {
                    "itemId": "67890",
                    "epid": "epid_001",  # Same EPID
                    "title": "Lower Price Product",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image2.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}],
                },
            ]
        }

        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client,  # Use same mock for both for simplicity
        }

        # Collect products
        products = await ebay_product_collector.collect_products("test query", 2)

        # Verify only one product (cheaper one) is returned
        assert len(products) == 1
        assert products[0]["epid"] == "epid_001"
        assert products[0]["title"] == "Lower Price Product"
        assert products[0]["totalPrice"] == 25.99
        assert products[0]["itemId"] == "67890"

    @pytest.mark.asyncio
    async def test_deduplication_by_item_id(
        self, ebay_product_collector, mock_ebay_auth_service
    ):
        """Test deduplication by item ID when EPID is not available"""
        # Mock eBay browse API client with duplicate item ID (no EPID)
        mock_browse_client = AsyncMock()
        mock_browse_client.search.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",  # Same item ID
                    "title": "Higher Price Product",
                    "price": {"value": 35.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image1.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}],
                },
                {
                    "itemId": "12345",  # Same item ID
                    "title": "Lower Price Product",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image2.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}],
                },
            ]
        }

        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client,  # Use same mock for both for simplicity
        }

        # Collect products
        products = await ebay_product_collector.collect_products("test query", 2)

        # Verify only one product (cheaper one) is returned
        assert len(products) == 1
        assert products[0]["itemId"] == "12345"
        assert products[0]["title"] == "Lower Price Product"
        assert products[0]["totalPrice"] == 25.99

    @pytest.mark.asyncio
    async def test_empty_response_handling(
        self, ebay_product_collector, mock_ebay_auth_service
    ):
        """Test handling of empty API responses"""
        # Mock eBay browse API client with empty response
        mock_browse_client = AsyncMock()
        mock_browse_client.search.return_value = {"itemSummaries": []}

        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client,  # Use same mock for both for simplicity
        }

        # Collect products
        products = await ebay_product_collector.collect_products("test query", 1)

        # Verify empty list is returned
        assert products == []

    @pytest.mark.asyncio
    async def test_insufficient_results_warning(
        self, ebay_product_collector, mock_ebay_auth_service
    ):
        """Test warning when insufficient results are found"""
        # Mock eBay browse API client with limited results
        mock_browse_client = AsyncMock()
        mock_browse_client.search.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "title": "Only Product",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image1.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}],
                }
            ]
        }

        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client,  # Use same mock for both for simplicity
        }

        # Collect products with higher limit
        products = await ebay_product_collector.collect_products("test query", 5)

        # Verify only available products are returned
        assert len(products) == 1
        assert products[0]["title"] == "Only Product"

    def test_get_source_name(self, ebay_product_collector):
        """Test source name returns 'ebay'"""
        assert ebay_product_collector.get_source_name() == "ebay"

    @pytest.mark.asyncio
    async def test_shipping_cost_calculation(
        self, ebay_product_collector, mock_ebay_auth_service
    ):
        """Test shipping cost calculation logic"""
        # Mock eBay browse API client with shipping options (FREE should be selected)
        mock_browse_client = AsyncMock()
        mock_browse_client.search.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "title": "Product with Shipping",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image1.jpg"},
                    "shippingOptions": [
                        {"shippingType": "FREE"},  # FREE should be selected first
                        {
                            "shippingType": "PAID",
                            "cost": {"value": 5.99, "currency": "USD"},
                        },
                    ],
                }
            ]
        }

        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client,  # Use same mock for both for simplicity
        }

        # Collect products
        products = await ebay_product_collector.collect_products("test query", 1)

        # Verify FREE shipping is selected
        assert len(products) == 1
        assert products[0]["shippingCost"] == 0  # FREE shipping should be selected
        assert products[0]["totalPrice"] == 25.99

    @pytest.mark.asyncio
    async def test_image_handling(self, ebay_product_collector, mock_ebay_auth_service):
        """Test image handling (primary + additional images)"""
        # Mock eBay browse API client with multiple images
        mock_browse_client = AsyncMock()
        mock_browse_client.search.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "title": "Product with Images",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/primary.jpg"},
                    "additionalImages": [
                        {"imageUrl": "https://example.com/additional1.jpg"},
                        {"imageUrl": "https://example.com/additional2.jpg"},
                        {"imageUrl": "https://example.com/additional3.jpg"},
                        {"imageUrl": "https://example.com/additional4.jpg"},
                        {"imageUrl": "https://example.com/additional5.jpg"},
                        {
                            "imageUrl": "https://example.com/additional6.jpg"
                        },  # Should be limited to 5
                    ],
                    "shippingOptions": [{"shippingType": "FREE"}],
                }
            ]
        }

        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client,  # Use same mock for both for simplicity
        }

        # Collect products
        products = await ebay_product_collector.collect_products("test query", 1)

        # Verify image handling. We should keep the primary image and the first
        # five additional images (limit of six total).
        assert len(products) == 1
        assert len(products[0]["images"]) == 6
        assert products[0]["images"][0] == "https://example.com/primary.jpg"
        assert products[0]["images"][-1] == "https://example.com/additional5.jpg"

    @pytest.mark.asyncio
    async def test_primary_image_field_handling(
        self, ebay_product_collector, mock_ebay_auth_service
    ):
        """Ensure we capture images when eBay uses primaryImage/additionalImages fields"""
        mock_browse_client = AsyncMock()
        mock_browse_client.search.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "title": "Product with Primary Field",
                    "price": {"value": 25.99, "currency": "USD"},
                    "primaryImage": {
                        "imageUrl": "https://example.com/primary-primaryImage.jpg"
                    },
                    "additionalImages": [
                        {"imageUrl": "https://example.com/extra1.jpg"},
                        {"imageUrl": "https://example.com/extra2.jpg"},
                    ],
                    "shippingOptions": [{"shippingType": "FREE"}],
                }
            ]
        }

        mock_browse_client.get_item.return_value = {
            "item": {
                "itemId": "12345",
                "title": "Product with Primary Field",
                "price": {"value": 25.99, "currency": "USD"},
                "primaryImage": {
                    "imageUrl": "https://example.com/primary-primaryImage.jpg"
                },
                "additionalImages": [
                    {"imageUrl": "https://example.com/extra1.jpg"},
                    {"imageUrl": "https://example.com/extra2.jpg"},
                ],
                "shippingOptions": [{"shippingType": "FREE"}],
            }
        }

        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client,
        }

        products = await ebay_product_collector.collect_products("primary field", 1)

        assert len(products) == 1
        assert products[0]["images"] == [
            "https://example.com/primary-primaryImage.jpg",
            "https://example.com/extra1.jpg",
            "https://example.com/extra2.jpg",
        ]

    @pytest.mark.asyncio
    async def test_brand_fallback_to_manufacturer(
        self, ebay_product_collector, mock_ebay_auth_service
    ):
        """Test brand fallback to manufacturer when brand is not available"""
        # Mock eBay browse API client with manufacturer but no brand
        mock_browse_client = AsyncMock()
        mock_browse_client.search.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "title": "Product with Manufacturer",
                    "manufacturer": "TestManufacturer",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image1.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}],
                }
            ]
        }

        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client,  # Use same mock for both for simplicity
        }

        # Collect products
        products = await ebay_product_collector.collect_products("test query", 1)

        # Verify manufacturer is used as brand fallback
        assert len(products) == 1
        assert products[0]["brand"] == "TestManufacturer"

    @pytest.mark.asyncio
    async def test_url_fallback_to_affiliate(
        self, ebay_product_collector, mock_ebay_auth_service
    ):
        """Test URL fallback to affiliate when main URL is not available"""
        # Mock eBay browse API client with affiliate URL but no main URL
        mock_browse_client = AsyncMock()
        mock_browse_client.search.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "title": "Product with Affiliate URL",
                    "itemAffiliateWebUrl": "https://ebay.com/affiliate",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image1.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}],
                }
            ]
        }

        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client,  # Use same mock for both for simplicity
        }

        # Collect products
        products = await ebay_product_collector.collect_products("test query", 1)

        # Verify affiliate URL is used as fallback
        assert len(products) == 1
        assert products[0]["url"] == "https://ebay.com/affiliate"
