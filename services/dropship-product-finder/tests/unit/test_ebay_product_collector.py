"""
Unit tests for eBay Browse API client and eBay product collector.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, Mock
from httpx import HTTPStatusError, RequestError

from services.ebay_browse_api_client import EbayBrowseApiClient
from collectors.ebay_product_collector import EbayProductCollector
from services.auth import eBayAuthService


@pytest.fixture
def mock_auth_service():
    """Mock authentication service"""
    auth = AsyncMock()
    auth.get_access_token = AsyncMock(return_value="test_token_123")
    auth.get_token = AsyncMock(return_value="test_token_123")  # Keep for backwards compatibility
    auth.refresh_token = AsyncMock()
    # Reset the mock to avoid state sharing between tests
    def reset_mock():
        auth.get_token.reset_mock()
        auth.refresh_token.reset_mock()
        auth.get_access_token.reset_mock()
    auth.reset_mock = reset_mock
    return auth


@pytest.fixture
def mock_ebay_auth_service():
    """Mock eBay auth service that doesn't fail with 401"""
    auth = AsyncMock()
    auth.get_access_token.return_value = "test_token_123"
    auth.get_token.return_value = "test_token_123"  # Keep for backwards compatibility
    auth.refresh_token = AsyncMock()
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
    with patch('services.ebay_browse_api_client.config', mock_config):
        with patch('config_loader.config', mock_config):
            return EbayBrowseApiClient(
                auth_service=mock_ebay_auth_service,
                marketplace_id="EBAY_US",
                base_url="https://api.sandbox.ebay.com/buy/browse/v1"
            )


@pytest.fixture
def ebay_product_collector(mock_ebay_auth_service, mock_config):
    """Create eBay product collector with mocked auth service"""
    with patch('config_loader.config', mock_config):
        with patch('services.ebay_browse_api_client.config', mock_config):
            return EbayProductCollector(
                data_root="/tmp/test",
                redis_client=mock_ebay_auth_service,
                marketplaces=["EBAY_US", "EBAY_UK"]
            )


class TestEbayBrowseApiClient:
    """Test cases for eBay Browse API client"""
    
    @pytest.mark.asyncio
    async def test_api_request_construction(self, ebay_browse_client, mock_ebay_auth_service):
        """Test API request construction with proper headers and parameters"""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"itemSummaries": []}
        
        # Mock auth service to return token directly
        mock_ebay_auth_service.get_access_token.return_value = "test_token_123"
        
        # Mock httpx.AsyncClient directly in the code
        with patch('httpx.AsyncClient') as mock_client_class:
            # Create a mock client that returns our response
            mock_client_instance = AsyncMock()
            mock_client_get = AsyncMock()
            mock_client_get.return_value = mock_response
            mock_client_instance.get = mock_client_get
            
            mock_client_class.return_value = mock_client_instance
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            # Make search request
            result = await ebay_browse_client.search("test query", 10, 0)
            
            # Verify auth service was called
            mock_ebay_auth_service.get_access_token.assert_called_once()
            
            # Verify API call was made with correct parameters
            mock_client_get.assert_called_once()
            call_args = mock_client_get.call_args
            
            assert call_args[0][0] == "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search"
            assert call_args.kwargs["params"]["q"] == "test query"
            assert call_args.kwargs["params"]["limit"] == 10
            assert call_args.kwargs["params"]["offset"] == 0
            assert call_args.kwargs["params"]["filter"] == (
                "buyingOptions:{FIXED_PRICE},"
                "returnsAccepted:true,"
                "deliveryCountry:US,"
                "maxDeliveryCost:0,"
                "price:[10..40],"
                "priceCurrency:USD,"
                "conditionIds:{1000}"
            )
            assert call_args.kwargs["params"]["fieldgroups"] == "EXTENDED"
            
            # Verify headers
            assert "Authorization" in call_args.kwargs["headers"]
            assert call_args.kwargs["headers"]["Authorization"] == "Bearer test_token_123"
            assert call_args.kwargs["headers"]["X-EBAY-C-MARKETPLACE-ID"] == "EBAY_US"
            assert call_args.kwargs["headers"]["Content-Type"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_successful_response_handling(self, ebay_browse_client, mock_ebay_auth_service):
        """Test handling of successful API responses"""
        # Mock successful response with item summaries
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "title": "Test Product",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image1.jpg"},
                    "itemWebUrl": "https://ebay.com/test"
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            # Make search request
            result = await ebay_browse_client.search("test query", 10)
            
            # Verify response is returned correctly
            assert result == mock_response.json.return_value
            assert "itemSummaries" in result
            assert len(result["itemSummaries"]) == 1
            assert result["itemSummaries"][0]["itemId"] == "12345"
    
    @pytest.mark.asyncio
    async def test_http_error_handling(self, mock_ebay_auth_service, mock_config):
        """Test handling of HTTP errors"""
        # Reset mock call counts
        mock_ebay_auth_service.get_access_token.reset_mock()
        mock_ebay_auth_service.get_token.reset_mock()
        mock_ebay_auth_service.refresh_token.reset_mock()
        
        # Create fresh client for this test
        with patch('services.ebay_browse_api_client.config', mock_config):
            with patch('config_loader.config', mock_config):
                ebay_browse_client = EbayBrowseApiClient(
                    auth_service=mock_ebay_auth_service,
                    marketplace_id="EBAY_US",
                    base_url="https://api.sandbox.ebay.com/buy/browse/v1"
                )
                
                # Mock 401 error
                mock_response = AsyncMock()
                mock_response.status_code = 401
                mock_response.text = "Unauthorized"
                
                with patch('httpx.AsyncClient') as mock_client_class:
                    mock_client = AsyncMock()
                    mock_client_class.return_value.__aenter__.return_value = mock_client
                    mock_client.get.return_value = mock_response
                    
                    # Make search request
                    result = await ebay_browse_client.search("test query", 10)
                    
                    # Verify empty response is returned on 401
                    assert result == {"itemSummaries": []}
                    # Verify token refresh was attempted (at least once for refresh)
                    mock_ebay_auth_service.refresh_token.assert_called()
                    mock_ebay_auth_service.get_access_token.assert_called()
    
    @pytest.mark.asyncio
    async def test_rate_limiting_retry(self, ebay_browse_client, mock_ebay_auth_service):
        """Test retry logic for rate limiting (429)"""
        # Mock 429 response first, then successful response
        mock_response_429 = AsyncMock()
        mock_response_429.status_code = 429
        mock_response_429.text = "Too Many Requests"
        
        mock_response_success = AsyncMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"itemSummaries": []}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = [mock_response_429, mock_response_success]
            
            with patch('asyncio.sleep') as mock_sleep:
                # Make search request
                result = await ebay_browse_client.search("test query", 10)
                
                # Verify retry was attempted
                assert mock_client.get.call_count == 2
                # Verify sleep was called for backoff
                mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_server_error_retry(self, ebay_browse_client, mock_ebay_auth_service):
        """Test retry logic for server errors (500, 502, 503, 504)"""
        # Mock 500 error first, then successful response
        mock_response_500 = AsyncMock()
        mock_response_500.status_code = 500
        mock_response_500.text = "Internal Server Error"
        
        mock_response_success = AsyncMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"itemSummaries": []}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = [mock_response_500, mock_response_success]
            
            with patch('asyncio.sleep') as mock_sleep:
                # Make search request
                result = await ebay_browse_client.search("test query", 10)
                
                # Verify retry was attempted
                assert mock_client.get.call_count == 2
                # Verify sleep was called for backoff
                mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self, ebay_browse_client, mock_ebay_auth_service):
        """Test behavior when max retries are exhausted"""
        # Mock persistent 500 error
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            with patch('asyncio.sleep') as mock_sleep:
                # Make search request
                result = await ebay_browse_client.search("test query", 10)
                
                # Verify max retries were attempted (should be 2 for MAX_RETRIES_BROWSE = 3)
                assert mock_client.get.call_count == 2  # MAX_RETRIES_BROWSE - 1
                # Verify sleep was called multiple times
                assert mock_sleep.call_count == 2  # MAX_RETRIES_BROWSE - 1
                # Verify empty response is returned
                assert result == {"itemSummaries": []}
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, ebay_browse_client, mock_ebay_auth_service):
        """Test handling of network errors"""
        # Mock network error
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = RequestError("Network error")
            
            with patch('asyncio.sleep') as mock_sleep:
                # Make search request
                result = await ebay_browse_client.search("test query", 10)
                
                # Verify retry was attempted
                assert mock_client.get.call_count == 2  # MAX_RETRIES_BROWSE - 1
                # Verify sleep was called for backoff (should be 1 call for 2 retries)
                assert mock_sleep.call_count == 1
                # Verify empty response is returned
                assert result == {"itemSummaries": []}
    
    @pytest.mark.asyncio
    async def test_query_length_limit(self, ebay_browse_client, mock_ebay_auth_service):
        """Test query length is limited to 100 characters"""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"itemSummaries": []}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            # Make search request with long query
            long_query = "a" * 150  # Exceeds 100 character limit
            result = await ebay_browse_client.search(long_query, 10)
            
            # Verify query was truncated
            call_args = mock_client.get.call_args
            assert len(call_args.kwargs["params"]["q"]) == 100
            assert call_args.kwargs["params"]["q"] == "a" * 100
    
    @pytest.mark.asyncio
    async def test_limit_parameter_clamping(self, ebay_browse_client, mock_ebay_auth_service):
        """Test limit parameter is clamped to 50 (eBay max per page)"""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"itemSummaries": []}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            # Make search request with limit > 50
            result = await ebay_browse_client.search("test query", 100)
            
            # Verify limit was clamped to 50
            call_args = mock_client.get.call_args
            assert call_args.kwargs["params"]["limit"] == 50
    
    @pytest.mark.asyncio
    async def test_extra_filter_addition(self, ebay_browse_client, mock_ebay_auth_service):
        """Test extra filter is properly added to existing filter"""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"itemSummaries": []}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            # Make search request with extra filter
            extra_filter = "conditionIds:{3000}"
            result = await ebay_browse_client.search("test query", 10, extra_filter=extra_filter)
            
            # Verify extra filter was added
            call_args = mock_client.get.call_args
            expected_filter = (
                "buyingOptions:{FIXED_PRICE},"
                "returnsAccepted:true,"
                "deliveryCountry:US,"
                "maxDeliveryCost:0,"
                "price:[10..40],"
                "priceCurrency:USD,"
                "conditionIds:{1000},"
                "conditionIds:{3000}"
            )
            assert call_args.kwargs["params"]["filter"] == expected_filter


class TestEbayProductCollector:
    """Test cases for eBay product collector"""
    
    @pytest.mark.asyncio
    async def test_product_data_extraction(self, ebay_product_collector, mock_ebay_auth_service):
        """Test product data extraction from API responses with detailed item calls"""
        # Mock the pre-initialized browse clients
        mock_browse_client = AsyncMock()
        
        # Mock search response
        search_response = {
            "itemSummaries": [
                {
                    "itemId": "12345",
                    "epid": "epid_001",
                    "title": "Test Product",
                    "brand": "TestBrand",
                    "manufacturer": "TestManufacturer",
                    "itemWebUrl": "https://ebay.com/test",
                    "itemAffiliateWebUrl": "https://ebay.com/affiliate",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image1.jpg"},
                    "shippingOptions": [
                        {"shippingType": "FREE"},
                        {"cost": {"value": 5.99, "currency": "USD"}}
                    ]
                }
            ]
        }
        
        # Mock detailed item response with additional images in galleryInfo
        detailed_item_response = {
            "item": {
                "itemId": "12345",
                "epid": "epid_001",
                "title": "Test Product",
                "brand": "TestBrand",
                "manufacturer": "TestManufacturer",
                "itemWebUrl": "https://ebay.com/test",
                "itemAffiliateWebUrl": "https://ebay.com/affiliate",
                "price": {"value": 25.99, "currency": "USD"},
                "image": {"imageUrl": "https://example.com/image1.jpg"},
                "galleryInfo": {
                    "imageVariations": [
                        {"imageUrl": "https://example.com/image1.jpg"},
                        {"imageUrl": "https://example.com/image2.jpg"},
                        {"imageUrl": "https://example.com/image3.jpg"},
                        {"imageUrl": "https://example.com/image4.jpg"},
                        {"imageUrl": "https://example.com/image5.jpg"},
                        {"imageUrl": "https://example.com/image6.jpg"}
                    ]
                },
                "shippingOptions": [
                    {"shippingType": "FREE"},
                    {"cost": {"value": 5.99, "currency": "USD"}}
                ]
            }
        }
        
        # Mock responses for search and get_item
        mock_browse_client.search.return_value = search_response
        mock_browse_client.get_item.return_value = detailed_item_response
        
        # Mock the browse clients that are already initialized
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client  # Use same mock for both for simplicity
        }
        
        # Collect products
        products = await ebay_product_collector.collect_products("test query", 1)
        
        # Verify browse client was called for both search and get_item
        mock_browse_client.search.assert_called_once()
        mock_browse_client.get_item.assert_called_once_with("12345", fieldgroups="ITEM")
        
        # Verify product transformation
        assert len(products) == 1
        product = products[0]
        assert product["id"] == "epid_001"
        assert product["title"] == "Test Product"
        assert product["brand"] == "TestBrand"
        assert product["url"] == "https://ebay.com/test"
        assert product["marketplace"] == "us"
        assert product["price"] == 25.99
        assert product["currency"] == "USD"
        assert product["epid"] == "epid_001"
        assert product["itemId"] == "12345"
        assert product["shippingCost"] == 0  # FREE shipping selected
        assert product["totalPrice"] == 25.99
        assert len(product["images"]) == 6  # primary + 5 additional from galleryInfo
        assert product["images"][0] == "https://example.com/image1.jpg"
        assert product["images"][1] == "https://example.com/image2.jpg"
        assert product["images"][5] == "https://example.com/image6.jpg"
    
    @pytest.mark.asyncio
    async def test_multiple_marketplaces(self, ebay_product_collector, mock_ebay_auth_service):
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
                    "shippingOptions": [{"shippingType": "FREE"}]
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
                    "shippingOptions": [{"shippingType": "FREE"}]
                }
            ]
        }
        
        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client_us,
            "EBAY_UK": mock_browse_client_uk
        }
        
        # Collect products
        products = await ebay_product_collector.collect_products("test query", 2)
        
        # Verify both marketplaces were queried
        mock_browse_client_us.search.assert_called_once_with(
            q="test query",
            limit=2,
            offset=0
        )
        mock_browse_client_uk.search.assert_called_once_with(
            q="test query",
            limit=2,
            offset=0
        )
        
        # Verify products from both marketplaces
        assert len(products) == 2
        us_product = next(p for p in products if p["marketplace"] == "us")
        uk_product = next(p for p in products if p["marketplace"] == "uk")
        assert us_product["title"] == "US Product"
        assert uk_product["title"] == "UK Product"
    
    @pytest.mark.asyncio
    async def test_error_handling_during_collection(self, ebay_product_collector, mock_ebay_auth_service):
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
                    "shippingOptions": [{"shippingType": "FREE"}]
                }
            ]
        }
        
        # Mock exception for second marketplace
        mock_browse_client_uk = AsyncMock()
        mock_browse_client_uk.search.side_effect = Exception("API Error")
        
        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client_us,
            "EBAY_UK": mock_browse_client_uk
        }
        
        # Collect products - should not raise exception
        products = await ebay_product_collector.collect_products("test query", 2)
        
        # Verify successful product from first marketplace is returned
        assert len(products) == 1
        assert products[0]["title"] == "US Product"
        assert products[0]["marketplace"] == "us"
    
    @pytest.mark.asyncio
    async def test_pagination_handling(self, ebay_product_collector, mock_ebay_auth_service):
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
                    "shippingOptions": [{"shippingType": "FREE"}]
                },
                {
                    "itemId": "67890",
                    "title": "Product 2",
                    "price": {"value": 19.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image2.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}]
                }
            ]
        }
        
        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client  # Use same mock for both for simplicity
        }
        
        # Collect products with limit > 50 (should be clamped)
        products = await ebay_product_collector.collect_products("test query", 100)
        
        # Verify browse client was called with original limit (clamping happens inside the client)
        assert mock_browse_client.search.call_count == 2
        for call in mock_browse_client.search.call_args_list:
            assert call.kwargs['limit'] == 100  # Original limit passed to search
            assert call.kwargs['offset'] == 0
        
        # Verify all products were collected
        assert len(products) == 2
    
    @pytest.mark.asyncio
    async def test_deduplication_by_epid(self, ebay_product_collector, mock_ebay_auth_service):
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
                    "shippingOptions": [{"shippingType": "FREE"}]
                },
                {
                    "itemId": "67890",
                    "epid": "epid_001",  # Same EPID
                    "title": "Lower Price Product",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image2.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}]
                }
            ]
        }
        
        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client  # Use same mock for both for simplicity
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
    async def test_deduplication_by_item_id(self, ebay_product_collector, mock_ebay_auth_service):
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
                    "shippingOptions": [{"shippingType": "FREE"}]
                },
                {
                    "itemId": "12345",  # Same item ID
                    "title": "Lower Price Product",
                    "price": {"value": 25.99, "currency": "USD"},
                    "image": {"imageUrl": "https://example.com/image2.jpg"},
                    "shippingOptions": [{"shippingType": "FREE"}]
                }
            ]
        }
        
        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client  # Use same mock for both for simplicity
        }
        
        # Collect products
        products = await ebay_product_collector.collect_products("test query", 2)
        
        # Verify only one product (cheaper one) is returned
        assert len(products) == 1
        assert products[0]["itemId"] == "12345"
        assert products[0]["title"] == "Lower Price Product"
        assert products[0]["totalPrice"] == 25.99
    
    @pytest.mark.asyncio
    async def test_empty_response_handling(self, ebay_product_collector, mock_ebay_auth_service):
        """Test handling of empty API responses"""
        # Mock eBay browse API client with empty response
        mock_browse_client = AsyncMock()
        mock_browse_client.search.return_value = {"itemSummaries": []}
        
        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client  # Use same mock for both for simplicity
        }
        
        # Collect products
        products = await ebay_product_collector.collect_products("test query", 1)
        
        # Verify empty list is returned
        assert products == []
    
    @pytest.mark.asyncio
    async def test_insufficient_results_warning(self, ebay_product_collector, mock_ebay_auth_service):
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
                    "shippingOptions": [{"shippingType": "FREE"}]
                }
            ]
        }
        
        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client  # Use same mock for both for simplicity
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
    async def test_shipping_cost_calculation(self, ebay_product_collector, mock_ebay_auth_service):
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
                        {"shippingType": "PAID", "cost": {"value": 5.99, "currency": "USD"}}
                    ]
                }
            ]
        }
        
        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client  # Use same mock for both for simplicity
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
                        {"imageUrl": "https://example.com/additional6.jpg"}  # Should be limited to 5
                    ],
                    "shippingOptions": [{"shippingType": "FREE"}]
                }
            ]
        }
        
        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client  # Use same mock for both for simplicity
        }
        
        # Collect products
        products = await ebay_product_collector.collect_products("test query", 1)
        
        # Verify image handling (only primary image since additionalImages doesn't exist in search response)
        assert len(products) == 1
        assert len(products[0]["images"]) == 1  # Only primary image available
        assert products[0]["images"][0] == "https://example.com/primary.jpg"
    
    @pytest.mark.asyncio
    async def test_brand_fallback_to_manufacturer(self, ebay_product_collector, mock_ebay_auth_service):
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
                    "shippingOptions": [{"shippingType": "FREE"}]
                }
            ]
        }
        
        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client  # Use same mock for both for simplicity
        }
        
        # Collect products
        products = await ebay_product_collector.collect_products("test query", 1)
        
        # Verify manufacturer is used as brand fallback
        assert len(products) == 1
        assert products[0]["brand"] == "TestManufacturer"
    
    @pytest.mark.asyncio
    async def test_url_fallback_to_affiliate(self, ebay_product_collector, mock_ebay_auth_service):
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
                    "shippingOptions": [{"shippingType": "FREE"}]
                }
            ]
        }
        
        # Mock the pre-initialized browse clients
        ebay_product_collector.browse_clients = {
            "EBAY_US": mock_browse_client,
            "EBAY_UK": mock_browse_client  # Use same mock for both for simplicity
        }
        
        # Collect products
        products = await ebay_product_collector.collect_products("test query", 1)
        
        # Verify affiliate URL is used as fallback
        assert len(products) == 1
        assert products[0]["url"] == "https://ebay.com/affiliate"