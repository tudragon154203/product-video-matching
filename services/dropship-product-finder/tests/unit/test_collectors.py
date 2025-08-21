"""
Unit tests for eBay collectors with authentication integration.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from collectors.ebay_product_collector import EbayProductCollector


@pytest.fixture
def mock_auth_service():
    """Mock authentication service"""
    auth = AsyncMock()
    auth.get_access_token.return_value = "test_token_123"
    auth._refresh_token = AsyncMock()
    auth.get_token = AsyncMock(return_value="test_token_123")
    auth.refresh_token = AsyncMock()
    return auth


@pytest.fixture
def ebay_collector(mock_auth_service):
    """Create eBay collector with mocked auth service"""
    return EbayProductCollector("/tmp/test", mock_auth_service)


class TestEbayProductCollector:
    """Test cases for eBay product collector"""
    
    @pytest.mark.asyncio
    async def test_collect_products_with_auth(self, ebay_collector, mock_auth_service):
        """Test product collection with authentication"""
        # Mock eBay browse API client response
        with patch('collectors.ebay_product_collector.EbayBrowseApiClient') as mock_browse_client:
            mock_browse_instance = AsyncMock()
            mock_browse_client.return_value = mock_browse_instance
            
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
                        ]
                    }
                ]
            }
            
            products = await ebay_collector.collect_products("test query", 1)
            
            # Verify browse client was created with auth service
            mock_browse_client.assert_called()
            
            # Verify browse client search was called (once per marketplace)
            assert mock_browse_instance.search.call_count == 3
            for call in mock_browse_instance.search.call_args_list:
                assert call.kwargs['q'] == "test query"
                assert call.kwargs['limit'] == 1
                assert call.kwargs['offset'] == 0
            
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
        collector = EbayProductCollector("/tmp/test", None)
        
        # Mock eBay browse API client response
        with patch('collectors.ebay_product_collector.EbayBrowseApiClient') as mock_browse_client:
            mock_browse_instance = AsyncMock()
            mock_browse_client.return_value = mock_browse_instance
            
            mock_browse_instance.search.return_value = {
                "itemSummaries": [
                    {
                        "itemId": "67890",
                        "title": "No Auth Product",
                        "seller": {"username": "no_auth_seller"},
                        "itemWebUrl": "https://ebay.com/noauth",
                        "imageUrls": [{"imageUrl": "https://example.com/noauth.jpg"}]
                    }
                ]
            }
            
            products = await collector.collect_products("no auth query", 1)
            
            # Verify browse client was created without auth service
            mock_browse_client.assert_called()
            
            # Verify browse client search was called (once per marketplace)
            assert mock_browse_instance.search.call_count == 3
            for call in mock_browse_instance.search.call_args_list:
                assert call.kwargs['q'] == "no auth query"
                assert call.kwargs['limit'] == 1
                assert call.kwargs['offset'] == 0
            
            # Verify product transformation
            assert len(products) == 1
            assert products[0]["id"] == "67890"
            assert products[0]["title"] == "No Auth Product"
    
    @pytest.mark.asyncio
    async def test_collect_products_token_refresh_on_401(self, ebay_collector, mock_auth_service):
        """Test token refresh on 401 error"""
        from httpx import HTTPStatusError
        
        # Mock eBay browse API client to raise 401 first, then succeed
        with patch('collectors.ebay_product_collector.EbayBrowseApiClient') as mock_browse_client:
            # First call fails with 401
            mock_browse_instance_401 = AsyncMock()
            mock_browse_instance_401.search.side_effect = HTTPStatusError(
                "401 Unauthorized", request=AsyncMock(), response=AsyncMock(status_code=401)
            )
            
            # Second call succeeds
            mock_browse_instance_success = AsyncMock()
            mock_browse_instance_success.search.return_value = {
                "itemSummaries": [
                    {
                        "itemId": "refreshed_token_product",
                        "title": "After Refresh Product",
                        "seller": {"username": "refreshed_seller"},
                        "itemWebUrl": "https://ebay.com/refreshed",
                        "imageUrls": [{"imageUrl": "https://example.com/refreshed.jpg"}]
                    }
                ]
            }
            
            # Mock the browse client to return different instances based on call
            mock_browse_client.side_effect = [mock_browse_instance_401, mock_browse_instance_success]
            
            products = await ebay_collector.collect_products("refresh query", 1)
            
            # Verify product was collected after refresh
            assert len(products) == 1
            assert products[0]["id"] == "refreshed_token_product"
    
    @pytest.mark.asyncio
    async def test_collect_products_empty_response(self, ebay_collector, mock_auth_service):
        """Test product collection with empty response"""
        # Mock empty eBay API response
        mock_response = AsyncMock()
        mock_response.json.return_value = {"itemSummaries": []}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            products = await ebay_collector.collect_products("empty query", 1)
            
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
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = HTTPStatusError(
                "500 Internal Server Error", request=AsyncMock(), response=mock_response
            )
            
            products = await ebay_collector.collect_products("error query", 1)
            
            # Verify empty list is returned on error
            assert products == []
    
    def test_get_source_name(self, ebay_collector):
        """Test source name returns 'ebay'"""
        assert ebay_collector.get_source_name() == "ebay"
    
    @pytest.mark.asyncio
    async def test_collect_products_rate_limiting(self, ebay_collector, mock_auth_service):
        """Test rate limiting in product collection"""
        # Mock eBay browse API client response
        with patch('collectors.ebay_product_collector.EbayBrowseApiClient') as mock_browse_client:
            mock_browse_instance = AsyncMock()
            mock_browse_client.return_value = mock_browse_instance
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
                            {"cost": {"value": 0, "currency": "USD"}}
                        ]
                    }
                ]
            }
            
            products = await ebay_collector.collect_products("test query", 1)
            
            # Verify browse client was called with correct parameters (once per marketplace)
            assert mock_browse_instance.search.call_count == 3
            for call in mock_browse_instance.search.call_args_list:
                assert call.kwargs['q'] == "test query"
                assert call.kwargs['limit'] == 1
                assert call.kwargs['offset'] == 0
            
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
        # Mock eBay API response with duplicate EPID
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "epid": "epid_001",
                    "title": "Product 1 - Higher Price",
                    "brand": "TestBrand",
                    "itemWebUrl": "https://ebay.com/test1",
                    "price": {"value": 35.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image1.jpg"},
                    "shippingOptions": [
                        {"shippingType": "FREE"}
                    ]
                },
                {
                    "itemId": "67890",
                    "epid": "epid_001",  # Same EPID
                    "title": "Product 2 - Lower Price",
                    "brand": "TestBrand",
                    "itemWebUrl": "https://ebay.com/test2",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image2.jpg"},
                    "shippingOptions": [
                        {"shippingType": "FREE"}
                    ]
                }
            ]
        }
        
        # Mock browse client to return products directly
        import httpx
        from services.ebay_browse_api_client import EbayBrowseApiClient
        
        with patch.object(ebay_collector, '_map_ebay_results') as mock_map:
            mock_map.side_effect = [
                [
                    {
                        "id": "epid_001", 
                        "title": "Product 1 - Higher Price",
                        "brand": "TestBrand",
                        "url": "https://ebay.com/test1",
                        "images": ["https://example.com/image1.jpg"],
                        "marketplace": "us",
                        "price": 35.99,
                        "currency": "USD",
                        "epid": "epid_001",
                        "itemId": "12345",
                        "totalPrice": 35.99,
                        "shippingCost": 0
                    },
                    {
                        "id": "epid_001",  # Same EPID
                        "title": "Product 2 - Lower Price",
                        "brand": "TestBrand",
                        "url": "https://ebay.com/test2",
                        "images": ["https://example.com/image2.jpg"],
                        "marketplace": "us",
                        "price": 25.99,
                        "currency": "USD",
                        "epid": "epid_001",
                        "itemId": "67890",
                        "totalPrice": 25.99,
                        "shippingCost": 0
                    }
                ]
            ]
            
            products = await ebay_collector.collect_products("dedup test", 2)
            
            # Should return only one product (the cheaper one)
            assert len(products) == 1
            assert products[0]["title"] == "Product 2 - Lower Price"
            assert products[0]["totalPrice"] == 25.99
            assert products[0]["itemId"] == "67890"