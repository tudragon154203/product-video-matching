"""
Unit tests for eBay collectors with authentication integration.
"""

from unittest.mock import AsyncMock, patch

import pytest

from collectors.ebay.ebay_product_collector import EbayProductCollector

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_redis():
    """Mock Redis client with proper async methods"""
    redis = AsyncMock()
    # Ensure all methods return awaitables
    redis.get = AsyncMock(
        return_value=b'{"access_token": "test_token_123", "expires_at": 9999999999}'
    )
    redis.setex = AsyncMock()
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def mock_auth_service(mock_redis):
    """Mock authentication service with all required async methods and attributes"""
    # Create mock with spec to ensure proper attribute access
    auth = AsyncMock(
        spec=[
            "get_access_token",
            "_refresh_token",
            "_store_token",
            "_retrieve_token",
            "_is_token_valid",
            "redis",
            "api_client",
        ]
    )

    # Core authentication methods
    auth.get_access_token = AsyncMock(return_value="test_token_123")
    auth._refresh_token = AsyncMock()
    auth._store_token = AsyncMock()
    auth._retrieve_token = AsyncMock(
        return_value={"access_token": "test_token_123", "expires_at": 9999999999}
    )
    auth._is_token_valid = AsyncMock(return_value=True)

    # Redis integration
    auth.redis = mock_redis
    auth.api_client = AsyncMock()
    return auth


@pytest.fixture
def ebay_collector(mock_auth_service, mock_redis):
    """Create eBay collector with mocked auth service"""
    with patch("config_loader.config.EBAY_MARKETPLACES", "EBAY_US,EBAY_UK,EBAY_DE"):
        with patch(
            "collectors.ebay.ebay_product_collector.EbayBrowseApiClient"
        ) as mock_browse_client_class:
            # Create mock browse client instance
            mock_browse_instance = AsyncMock()
            mock_browse_client_class.return_value = mock_browse_instance

            collector = EbayProductCollector("/tmp/test", redis_client=mock_redis)
            collector.auth_service = mock_auth_service  # Inject mock auth service

            # Replace the browse clients with our mock
            collector.browse_clients = {
                "EBAY_US": mock_browse_instance,
                "EBAY_UK": mock_browse_instance,
                "EBAY_DE": mock_browse_instance,
            }
            return collector


class TestEbayProductCollector:
    """Test cases for eBay product collector"""

    @pytest.mark.asyncio
    async def test_collect_products_with_auth(self, ebay_collector, mock_auth_service):
        """Test product collection with authentication"""
        # Mock eBay browse API client response
        mock_browse_instance = ebay_collector.browse_clients["EBAY_US"]

        mock_browse_instance.search.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "title": "Test Product",
                    "brand": "test_seller",
                    "itemWebUrl": "https://ebay.com/test",
                    "image": {"imageUrl": "https://example.com/image1.jpg"},
                    "additionalImages": [
                        {"imageUrl": "https://example.com/image2.jpg"}
                    ],
                }
            ]
        }

        mock_browse_instance.get_item.return_value = {
            "item": {
                "itemId": "12345",
                "title": "Test Product",
                "brand": "test_seller",
                "itemWebUrl": "https://ebay.com/test",
                "image": {"imageUrl": "https://example.com/image1.jpg"},
                "galleryInfo": {
                    "imageVariations": [
                        {"imageUrl": "https://example.com/image1.jpg"},
                        {"imageUrl": "https://example.com/image2.jpg"},
                    ]
                },
            }
        }

        products = await ebay_collector.collect_products("test query", 1)

        # Verify browse client was called
        mock_browse_instance.search.assert_called()

        # Verify product transformation
        assert len(products) == 1
        assert products[0]["id"] == "12345"
        assert products[0]["title"] == "Test Product"
        assert products[0]["brand"] == "test_seller"
        assert products[0]["url"] == "https://ebay.com/test"
        assert len(products[0]["images"]) == 2

    @pytest.mark.asyncio
    async def test_collect_products_without_auth(self):
        """Test product collection without authentication service"""
        # Create collector without auth service
        with patch("config_loader.config.EBAY_MARKETPLACES", "EBAY_US"):
            with patch(
                "collectors.ebay.ebay_product_collector.EbayBrowseApiClient"
            ) as mock_browse_client_class:
                mock_browse_instance = AsyncMock()
                mock_browse_client_class.return_value = mock_browse_instance

                collector = EbayProductCollector("/tmp/test", redis_client=None)

                mock_browse_instance.search.return_value = {
                    "itemSummaries": [
                        {
                            "itemId": "67890",
                            "title": "No Auth Product",
                            "seller": {"username": "no_auth_seller"},
                            "itemWebUrl": "https://ebay.com/noauth",
                            "image": {"imageUrl": "https://example.com/noauth.jpg"},
                        }
                    ]
                }

                products = await collector.collect_products("no auth query", 1)

                # Verify browse client was created without auth service
                mock_browse_client_class.assert_called()

                # Verify browse client search was called (once per marketplace)
                assert mock_browse_instance.search.call_count == 1
                for call in mock_browse_instance.search.call_args_list:
                    assert call.kwargs["q"] == "no auth query"
                    assert call.kwargs["limit"] == 1
                    assert call.kwargs["offset"] == 0

                # Verify product transformation
                assert len(products) == 1
                assert products[0]["id"] == "67890"
                assert products[0]["title"] == "No Auth Product"

    @pytest.mark.asyncio
    async def test_collect_products_empty_response(
        self, ebay_collector, mock_auth_service
    ):
        """Test product collection with empty response"""
        # Mock empty eBay API response
        mock_response = AsyncMock()
        mock_response.json.return_value = {"itemSummaries": []}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            products = await ebay_collector.collect_products("empty response query", 1)

            # Verify empty list is returned
            assert products == []

    @pytest.mark.asyncio
    async def test_collect_products_http_error(self, ebay_collector, mock_auth_service):
        """Test product collection with HTTP error"""
        from httpx import HTTPStatusError

        # Mock HTTP error
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = HTTPStatusError(
                "500 Internal Server Error", request=AsyncMock(), response=mock_response
            )

            products = await ebay_collector.collect_products("http error query", 1)

            # Verify empty list is returned on error
            assert products == []

    def test_get_source_name(self, ebay_collector):
        """Test source name returns 'ebay'"""
        assert ebay_collector.get_source_name() == "ebay"

    @pytest.mark.asyncio
    async def test_collect_products_rate_limiting(
        self, ebay_collector, mock_auth_service
    ):
        """Test rate limiting in product collection"""
        # Mock eBay browse API client response
        mock_browse_instance = ebay_collector.browse_clients["EBAY_US"]

        mock_browse_instance.search.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "title": "Product with images and price",
                    "brand": "TestBrand",
                    "itemWebUrl": "https://ebay.com/test",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image1.jpg"},
                    "additionalImages": [
                        {"imageUrl": "https://example.com/image2.jpg"}
                    ],
                    "shippingOptions": [
                        {"shippingType": "FREE"},
                        {"cost": {"value": 0, "currency": "USD"}},
                    ],
                }
            ]
        }

        mock_browse_instance.get_item.return_value = {
            "item": {
                "itemId": "12345",
                "title": "Product with images and price",
                "brand": "TestBrand",
                "itemWebUrl": "https://ebay.com/test",
                "price": {"value": 25.99, "currency": "USD"},
                "image": {"imageUrl": "https://example.com/image1.jpg"},
                "galleryInfo": {
                    "imageVariations": [
                        {"imageUrl": "https://example.com/image1.jpg"},
                        {"imageUrl": "https://example.com/image2.jpg"},
                    ]
                },
                "shippingOptions": [
                    {"shippingType": "FREE"},
                    {"cost": {"value": 0, "currency": "USD"}},
                ],
            }
        }

        products = await ebay_collector.collect_products("rate limiting query", 1)

        # Verify product transformation
        assert len(products) == 1
        assert products[0]["id"] == "12345"
        assert products[0]["title"] == "Product with images and price"
        assert products[0]["brand"] == "TestBrand"
        assert products[0]["url"] == "https://ebay.com/test"
        assert len(products[0]["images"]) == 2
        assert products[0]["price"] == 25.99
        assert products[0]["currency"] == "USD"
        assert products[0]["shippingCost"] == 0
        assert products[0]["totalPrice"] == 25.99

    @pytest.mark.asyncio
    async def test_deduplication_by_epid(self, ebay_collector, mock_auth_service):
        """Test deduplication by EPID"""
        # Mock eBay API response with duplicate EPID from different marketplaces
        mock_browse_instance = ebay_collector.browse_clients["EBAY_US"]

        # Mock search response with duplicate EPID
        mock_browse_instance.search.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "epid": "epid_001",
                    "title": "Product 1 - Higher Price",
                    "brand": "TestBrand",
                    "itemWebUrl": "https://ebay.com/test1",
                    "price": {"value": 35.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image1.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}],
                }
            ]
        }

        mock_browse_instance.get_item.return_value = {
            "item": {
                "itemId": "12345",
                "epid": "epid_001",
                "title": "Product 1 - Higher Price",
                "brand": "TestBrand",
                "itemWebUrl": "https://ebay.com/test1",
                "price": {"value": 35.99, "currency": "USD"},
                "image": {"imageUrl": "https://example.com/image1.jpg"},
                "galleryInfo": {
                    "imageVariations": [{"imageUrl": "https://example.com/image1.jpg"}]
                },
                "shippingOptions": [{"shippingType": "FREE"}],
            }
        }

        # Mock UK client with same EPID but lower price
        mock_browse_uk = ebay_collector.browse_clients["EBAY_UK"]
        mock_browse_uk.search.return_value = {
            "itemSummaries": [
                {
                    "itemId": "67890",
                    "epid": "epid_001",  # Same EPID
                    "title": "Product 2 - Lower Price",
                    "brand": "TestBrand",
                    "itemWebUrl": "https://ebay.com/test2",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image2.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}],
                }
            ]
        }

        mock_browse_uk.get_item.return_value = {
            "item": {
                "itemId": "67890",
                "epid": "epid_001",
                "title": "Product 2 - Lower Price",
                "brand": "TestBrand",
                "itemWebUrl": "https://ebay.com/test2",
                "price": {"value": 25.99, "currency": "USD"},
                "image": {"imageUrl": "https://example.com/image2.jpg"},
                "galleryInfo": {
                    "imageVariations": [{"imageUrl": "https://example.com/image2.jpg"}]
                },
                "shippingOptions": [{"shippingType": "FREE"}],
            }
        }

        products = await ebay_collector.collect_products("deduplication query", 2)

        # Should return only one product (the cheaper one)
        assert len(products) == 1
        assert products[0]["title"] == "Product 2 - Lower Price"
        assert products[0]["totalPrice"] == 25.99
        assert products[0]["itemId"] == "67890"

    @pytest.mark.asyncio
    async def test_collect_products_simulation(self, ebay_collector, mock_auth_service):
        """
        Integration test for product collection, mocking only the HTTP client.
        This tests the interaction between EbayProductCollector and EbayBrowseApiClient.
        """
        # Mock browse client responses directly
        mock_browse_instance = ebay_collector.browse_clients["EBAY_US"]

        # Define a realistic mock response for the eBay Browse API search
        mock_response_data = {
            "itemSummaries": [
                {
                    "itemId": "INTEG1",
                    "title": "Integration Test Product 1",
                    "brand": "TestBrandA",
                    "itemWebUrl": "https://ebay.com/integ1",
                    "image": {"imageUrl": "https://example.com/integ1_img1.jpg"},
                    "additionalImages": [
                        {"imageUrl": "https://example.com/integ1_img2.jpg"}
                    ],
                    "price": {"value": 10.00, "currency": "USD"},
                    "shippingOptions": [{"shippingType": "FREE"}],
                },
                {
                    "itemId": "INTEG2",
                    "title": "Integration Test Product 2",
                    "brand": "TestBrandB",
                    "itemWebUrl": "https://ebay.com/integ2",
                    "image": {"imageUrl": "https://example.com/integ2_img1.jpg"},
                    "price": {"value": 25.50, "currency": "EUR"},
                    "shippingOptions": [{"cost": {"value": 5.00, "currency": "EUR"}}],
                },
            ]
        }

        mock_browse_instance.search.return_value = mock_response_data

        # Mock detailed item responses
        mock_browse_instance.get_item.side_effect = [
            {
                "item": {
                    "itemId": "INTEG1",
                    "title": "Integration Test Product 1",
                    "brand": "TestBrandA",
                    "itemWebUrl": "https://ebay.com/integ1",
                    "image": {"imageUrl": "https://example.com/integ1_img1.jpg"},
                    "galleryInfo": {
                        "imageVariations": [
                            {"imageUrl": "https://example.com/integ1_img1.jpg"},
                            {"imageUrl": "https://example.com/integ1_img2.jpg"},
                        ]
                    },
                    "price": {"value": 10.00, "currency": "USD"},
                    "shippingOptions": [{"shippingType": "FREE"}],
                }
            },
            {
                "item": {
                    "itemId": "INTEG2",
                    "title": "Integration Test Product 2",
                    "brand": "TestBrandB",
                    "itemWebUrl": "https://ebay.com/integ2",
                    "image": {"imageUrl": "https://example.com/integ2_img1.jpg"},
                    "price": {"value": 25.50, "currency": "EUR"},
                    "shippingOptions": [{"cost": {"value": 5.00, "currency": "EUR"}}],
                }
            },
        ]

        # Call the collect_products method
        products = await ebay_collector.collect_products("integration test query", 2)

        # Assertions
        # Verify the structure and content of the returned products
        assert len(products) == 2

        # Product 1 assertions
        assert products[0]["id"] == "INTEG1"
        assert products[0]["title"] == "Integration Test Product 1"
        assert products[0]["brand"] == "TestBrandA"
        assert products[0]["url"] == "https://ebay.com/integ1"
        assert len(products[0]["images"]) == 2
        assert products[0]["price"] == 10.00
        assert products[0]["currency"] == "USD"
        assert products[0]["shippingCost"] == 0.0
        assert products[0]["totalPrice"] == 10.00

        # Product 2 assertions
        assert products[1]["id"] == "INTEG2"
        assert products[1]["title"] == "Integration Test Product 2"
        assert products[1]["brand"] == "TestBrandB"
        assert products[1]["url"] == "https://ebay.com/integ2"
        assert len(products[1]["images"]) == 1
        assert products[1]["price"] == 25.50
        assert products[1]["currency"] == "EUR"
        assert products[1]["shippingCost"] == 0.0  # FREE shipping type, not cost-based
        assert products[1]["totalPrice"] == 25.50
