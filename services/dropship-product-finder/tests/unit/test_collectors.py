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
        # Mock eBay API response
        mock_response = AsyncMock()
        # Make json() return the data directly instead of a coroutine
        mock_response.json.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "title": "Test Product",
                    "seller": {"username": "test_seller"},
                    "itemWebUrl": "https://ebay.com/test",
                    "imageUrls": [
                        {"imageUrl": "https://example.com/image1.jpg"},
                        {"imageUrl": "https://example.com/image2.jpg"}
                    ]
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            products = await ebay_collector.collect_products("test query", 1)
            
            # Verify auth service was called
            mock_auth_service.get_access_token.assert_called_once()
            
            # Verify API call was made with correct headers
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert "Authorization" in call_args.kwargs["headers"]
            assert call_args.kwargs["headers"]["Authorization"] == "Bearer test_token_123"
            
            # Verify product transformation
            assert len(products) == 1
            assert products[0]["id"] == "12345"
            assert products[0]["title"] == "Test Product"
            assert products[0]["brand"] == "test_seller"
            assert products[0]["url"] == "https://ebay.com/test"
            assert len(products[0]["images"]) == 2
    
    @pytest.mark.asyncio
    async def test_collect_products_without_auth(self, ebay_collector):
        """Test product collection without authentication service"""
        # Create collector without auth service
        collector = EbayProductCollector("/tmp/test")
        
        # Mock eBay API response
        mock_response = AsyncMock()
        mock_response.json.return_value = {
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
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            products = await collector.collect_products("no auth query", 1)
            
            # Verify API call was made without auth header
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert "Authorization" not in call_args.kwargs["headers"]
            
            # Verify product transformation
            assert len(products) == 1
            assert products[0]["id"] == "67890"
            assert products[0]["title"] == "No Auth Product"
    
    @pytest.mark.asyncio
    async def test_collect_products_token_refresh_on_401(self, ebay_collector, mock_auth_service):
        """Test token refresh on 401 error"""
        from httpx import HTTPStatusError
        
        # Mock 401 response first, then successful response
        mock_response_401 = AsyncMock()
        mock_response_401.status_code = 401
        mock_response_401.reason_phrase = "Unauthorized"
        
        mock_response_success = AsyncMock()
        mock_response_success.json.return_value = {
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
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # First call returns 401, second call succeeds
            mock_client.get.side_effect = [
                HTTPStatusError("401 Unauthorized", request=AsyncMock(), response=mock_response_401),
                mock_response_success
            ]
            
            products = await ebay_collector.collect_products("refresh query", 1)
            
            # Verify token refresh was called
            mock_auth_service._refresh_token.assert_called_once()
            
            # Verify auth service was called twice (original + refresh)
            assert mock_auth_service.get_access_token.call_count == 2
            
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
        # Mock eBay API response
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "itemSummaries": [
                {
                    "itemId": "rate_limited_product",
                    "title": "Rate Limited Product",
                    "seller": {"username": "rate_limited_seller"},
                    "itemWebUrl": "https://ebay.com/rate_limited",
                    "imageUrls": [{"imageUrl": "https://example.com/rate_limited.jpg"}]
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            with patch.object(ebay_collector, '_enforce_rate_limit') as mock_rate_limit:
                await ebay_collector.collect_products("rate query", 1)
                
                # Verify rate limiting was called
                mock_rate_limit.assert_called_once()