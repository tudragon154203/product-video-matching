# Unit Test for eBay Auth API Client

from services.ebay_auth_api_client import EbayAuthAPIClient
from httpx import Response, Request, HTTPStatusError, RequestError
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import pytest

pytestmark = pytest.mark.unit

# Import the client to be tested

# --- FIX: Mock config_loader module before importing client ---
# This is necessary because the client module imports 'config_loader' which is not on the path.
mock_config_module = MagicMock()
sys.modules['config_loader'] = mock_config_module


@pytest.fixture
def auth_client():
    """Fixture to create an EbayAuthAPIClient instance for testing."""
    return EbayAuthAPIClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        token_url="https://api.ebay.com/identity/v1/oauth2/token",
        scopes="https://api.ebay.com/oauth/api_scope"
    )


@pytest.fixture
def mock_httpx_client():
    """Fixture for a mock httpx.AsyncClient instance."""
    mock = AsyncMock()
    mock.post = AsyncMock()
    mock.aclose = AsyncMock()
    return mock


# --- Test for successful token request ---

@pytest.mark.asyncio
async def test_request_access_token_success(auth_client):
    """Test successful token request returns correct token data."""
    # Mock successful response
    expected_token_data = {
        "access_token": "test_access_token",
        "token_type": "Bearer",
        "expires_in": 7200,
        "refresh_token": "test_refresh_token",
        "refresh_token_expires_in": 47304000,
        "eBayTokenType": "User Token"
    }

    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = expected_token_data
    mock_response.text = str(expected_token_data)
    mock_response.request = Request(method="POST", url="https://api.ebay.com/identity/v1/oauth2/token")

    # Mock the httpx.AsyncClient context manager
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client_instance = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client_instance
        mock_client_class.return_value.__aexit__.return_value = None
        mock_client_instance.post.return_value = mock_response

        # Call the method
        result = await auth_client.request_access_token()

        # Verify the result
        assert result == expected_token_data

        # Verify the HTTP call was made correctly
        mock_client_instance.post.assert_called_once_with(
            auth_client.token_url,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": "Basic dGVzdF9jbGllbnRfaWQ6dGVzdF9jbGllbnRfc2VjcmV0"
            },
            data={"grant_type": "client_credentials", "scope": auth_client.scopes}
        )

        # Verify response.raise_for_status() was called
        mock_response.raise_for_status.assert_called_once()


# --- Test for HTTPStatusError ---

@pytest.mark.asyncio
async def test_request_access_token_http_status_error(auth_client):
    """Test HTTPStatusError is handled correctly and re-raised."""
    # Mock HTTP error response
    error_response = MagicMock(spec=Response)
    error_response.status_code = 401
    error_response.text = "Unauthorized"
    error_response.request = Request(method="POST", url="https://api.ebay.com/identity/v1/oauth2/token")

    # Create the HTTPStatusError
    http_error = HTTPStatusError(
        "401 Unauthorized",
        request=Request(method="POST", url="https://api.ebay.com/identity/v1/oauth2/token"),
        response=error_response
    )

    # Mock the httpx.AsyncClient context manager to raise HTTPStatusError
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client_instance = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client_instance
        mock_client_class.return_value.__aexit__.return_value = None
        mock_client_instance.post.side_effect = http_error

        # Call the method and expect HTTPStatusError to be raised
        with pytest.raises(HTTPStatusError) as exc_info:
            await auth_client.request_access_token()

        # Verify the error details
        assert exc_info.value.response.status_code == 401
        assert exc_info.value.response.text == "Unauthorized"

        # Verify the HTTP call was made
        mock_client_instance.post.assert_called_once()


# --- Test for RequestError ---

@pytest.mark.asyncio
async def test_request_access_token_request_error(auth_client):
    """Test RequestError is handled correctly and re-raised."""
    # Mock network error
    network_error = RequestError("Connection refused")

    # Mock the httpx.AsyncClient context manager to raise RequestError
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client_instance = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client_instance
        mock_client_class.return_value.__aexit__.return_value = None
        mock_client_instance.post.side_effect = network_error

        # Call the method and expect RequestError to be raised
        with pytest.raises(RequestError) as exc_info:
            await auth_client.request_access_token()

        # Verify the error message
        assert "Connection refused" in str(exc_info.value)

        # Verify the HTTP call was made
        mock_client_instance.post.assert_called_once()


# --- Test for unexpected Exception ---

@pytest.mark.asyncio
async def test_request_access_token_unexpected_exception(auth_client):
    """Test unexpected exceptions are handled correctly and re-raised."""
    # Mock unexpected error
    unexpected_error = Exception("Unexpected error occurred")

    # Mock the httpx.AsyncClient context manager to raise unexpected error
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client_instance = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client_instance
        mock_client_class.return_value.__aexit__.return_value = None
        mock_client_instance.post.side_effect = unexpected_error

        # Call the method and expect Exception to be raised
        with pytest.raises(Exception) as exc_info:
            await auth_client.request_access_token()

        # Verify the error message
        assert "Unexpected error occurred" in str(exc_info.value)

        # Verify the HTTP call was made
        mock_client_instance.post.assert_called_once()
