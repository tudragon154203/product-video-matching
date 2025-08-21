import asyncio
from unittest.mock import AsyncMock, Mock
from services.ebay_browse_api_client import EbayBrowseApiClient

# Create a mock auth service with the expected interface
mock_auth = AsyncMock()
mock_auth.get_token.return_value = "test_token_123"
mock_auth.refresh_token = AsyncMock()

# Create mock config
mock_config = Mock()
mock_config.MAX_RETRIES_BROWSE = 3
mock_config.TIMEOUT_SECS_BROWSE = 30.0
mock_config.BACKOFF_BASE_BROWSE = 1.5

# Create the client
client = EbayBrowseApiClient(
    auth_service=mock_auth,
    marketplace_id="EBAY_US",
    base_url="https://api.sandbox.ebay.com/buy/browse/v1"
)

# Mock successful response
mock_response = AsyncMock()
mock_response.status_code = 200
mock_response.json.return_value = {"itemSummaries": []}

# Mock httpx client
import httpx
from unittest.mock import patch

async def test_client():
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        
        # Make search request
        result = await client.search("test query", 10, 0)
        
        print("Search completed successfully")
        print("Result:", result)
        print("Auth service get_token called:", mock_auth.get_token.called)
        print("Auth service refresh_token called:", mock_auth.refresh_token.called)
        print("HTTP client get called:", mock_client.get.called)

# Run the test
asyncio.run(test_client())