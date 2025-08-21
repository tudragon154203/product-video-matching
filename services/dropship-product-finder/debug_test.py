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

print("Client created successfully")
print("Mock has get_token:", hasattr(mock_auth, 'get_token'))
print("Mock has refresh_token:", hasattr(mock_auth, 'refresh_token'))