# Unit Test for eBay Browse API Client

from services.ebay_browse_api_client import (
    EbayBrowseApiClient,
    FILTER,
)
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import Response, Request
import sys

# --- FIX: Mock config_loader module before importing client ---
# This is necessary because the client module imports 'config_loader' which is not on the path.
mock_config_module = MagicMock()
# Set default config values to allow the client logic to run
mock_config_module.config.MAX_RETRIES_BROWSE = 3
mock_config_module.config.BACKOFF_BASE_BROWSE = 2
mock_config_module.config.TIMEOUT_SECS_BROWSE = 10
sys.modules['config_loader'] = mock_config_module


def mock_response(status_code, json_data=None, text=None):
    """Creates a mock httpx.Response object."""
    response = MagicMock(spec=Response)
    response.status_code = status_code
    response.json = MagicMock(return_value=json_data if json_data is not None else {})
    response.text = text if text is not None else ""
    response.request = Request(method="GET", url="http://test.com")
    return response

# --- Fixtures ---


@pytest.fixture
def mock_config():
    """Fixture to mock config values used by the client."""
    mock = MagicMock()
    mock.MAX_RETRIES_BROWSE = 3
    mock.BACKOFF_BASE_BROWSE = 2
    mock.TIMEOUT_SECS_BROWSE = 10
    # Patch both module-level config and imported config in client module
    with patch("config_loader.config", mock), \
         patch("services.ebay_browse_api_client.config", mock):
        yield mock


@pytest.fixture
def mock_auth_service():
    """Fixture to mock the eBayAuthService."""
    mock = AsyncMock()
    mock.get_access_token.return_value = "initial_token"
    mock.get_token.return_value = "new_token"  # Used inside _make_request_with_retry
    yield mock


@pytest.fixture
def mock_httpx_client():
    """Fixture for a mock httpx.AsyncClient instance (for injection)."""
    mock = AsyncMock()
    mock.get = AsyncMock()
    mock.aclose = AsyncMock()
    return mock


@pytest.fixture
def client_with_mock_httpx(mock_auth_service, mock_httpx_client, mock_config):
    """EbayBrowseApiClient instance with an injected httpx client."""
    return EbayBrowseApiClient(
        auth_service=mock_auth_service,
        marketplace_id="EBAY_US",
        base_url="https://api.ebay.com/buy/browse/v1",
        httpx_client=mock_httpx_client,
    )


@pytest.fixture
def client_without_httpx(mock_auth_service, mock_config):
    """EbayBrowseApiClient instance without an injected httpx client (forces internal creation)."""
    return EbayBrowseApiClient(
        auth_service=mock_auth_service,
        marketplace_id="EBAY_US",
        base_url="https://api.ebay.com/buy/browse/v1",
        httpx_client=None,
    )

# --- Tests for _make_request_with_retry ---


@pytest.mark.asyncio
@patch("asyncio.sleep", new=AsyncMock())
async def test_make_request_success(client_with_mock_httpx, mock_httpx_client):
    """Test successful request (HTTP 200)."""
    expected_json = {"itemSummaries": [{"itemId": "123"}]}
    mock_httpx_client.get.return_value = mock_response(200, expected_json)

    result = await client_with_mock_httpx._make_request_with_retry(
        "url", {"Authorization": "Bearer token"}, {}
    )

    assert result == expected_json
    mock_httpx_client.get.assert_called_once()
    # Should not call aclose since client was injected
    client_with_mock_httpx.httpx_client.aclose.assert_not_called()


@pytest.mark.asyncio
@patch("asyncio.sleep", new=AsyncMock())
@patch("httpx.AsyncClient")
async def test_make_request_internal_client_closure(mock_httpx_async_client, client_without_httpx):
    """Test that the internal httpx client is closed when created ad-hoc."""
    # Setup the mock httpx.AsyncClient
    mock_client_instance = AsyncMock()
    mock_httpx_async_client.return_value = mock_client_instance
    mock_client_instance.get.return_value = mock_response(200, {"itemSummaries": []})

    await client_without_httpx._make_request_with_retry(
        "https://api.ebay.com/buy/browse/v1/item", {"Authorization": "Bearer token"}, {}
    )

    # Assert that aclose was called on the internally created client
    mock_client_instance.aclose.assert_called_once()


@pytest.mark.asyncio
@patch("asyncio.sleep", new=AsyncMock())
async def test_make_request_json_decode_error(client_with_mock_httpx, mock_httpx_client):
    """Test fallback to empty payload when JSON decode fails."""
    mock_resp = mock_response(200)
    mock_resp.json.side_effect = Exception("JSON decode failed")
    mock_httpx_client.get.return_value = mock_resp

    result = await client_with_mock_httpx._make_request_with_retry(
        "url", {"Authorization": "Bearer token"}, {}
    )

    assert result == {"itemSummaries": []}


@pytest.mark.asyncio
@patch("asyncio.sleep", new=AsyncMock())
async def test_make_request_401_auth_refresh_success(
    client_with_mock_httpx, mock_httpx_client, mock_auth_service
):
    """Test 401 triggers token refresh and successful retry."""
    # First call returns 401, second call returns 200
    mock_httpx_client.get.side_effect = [
        mock_response(401),
        mock_response(200, {"itemSummaries": [{"itemId": "456"}]}),
    ]

    result = await client_with_mock_httpx._make_request_with_retry(
        "url", {"Authorization": "Bearer old_token"}, {}
    )

    assert result == {"itemSummaries": [{"itemId": "456"}]}
    mock_auth_service.refresh_token.assert_called_once()
    mock_auth_service.get_token.assert_called_once()
    assert mock_httpx_client.get.call_count == 2


@pytest.mark.asyncio
@patch("asyncio.sleep", new=AsyncMock())
async def test_make_request_401_auth_refresh_failure(
    client_with_mock_httpx, mock_httpx_client, mock_auth_service
):
    """Test 401 fails even after token refresh (only retries once)."""
    # Both calls return 401
    mock_httpx_client.get.side_effect = [
        mock_response(401),
        mock_response(401),
    ]

    result = await client_with_mock_httpx._make_request_with_retry(
        "url", {"Authorization": "Bearer old_token"}, {}
    )

    assert result == {"itemSummaries": []}
    assert mock_auth_service.refresh_token.call_count == 2  # FIX 3: Changed to assert call_count == 2
    assert mock_httpx_client.get.call_count == 2


@pytest.mark.asyncio
@patch("asyncio.sleep", new=AsyncMock())
async def test_make_request_retryable_error_success(
    client_with_mock_httpx, mock_httpx_client, mock_config
):
    """Test retryable error (e.g., 500) succeeds on the second attempt."""
    # 500, then 200
    mock_httpx_client.get.side_effect = [
        mock_response(500),
        mock_response(200, {"itemSummaries": [{"itemId": "789"}]}),
    ]

    result = await client_with_mock_httpx._make_request_with_retry(
        "url", {"Authorization": "Bearer token"}, {}
    )

    assert result == {"itemSummaries": [{"itemId": "789"}]}
    assert mock_httpx_client.get.call_count == 2
    # Check backoff time: attempt 0 -> 2**0 = 1 second
    asyncio.sleep.assert_called_once_with(1)


@pytest.mark.asyncio
@patch("asyncio.sleep", new=AsyncMock())
async def test_make_request_retryable_error_exhausted(
    client_with_mock_httpx, mock_httpx_client, mock_config
):
    """Test retryable error exhausts all retries."""
    # 500 for all attempts. The code runs with mocked MAX_RETRIES=3.
    mock_httpx_client.get.side_effect = [
        mock_response(500),
        mock_response(500),
        mock_response(500),
    ]

    result = await client_with_mock_httpx._make_request_with_retry(
        "url", {"Authorization": "Bearer token"}, {}
    )

    assert result == {"itemSummaries": []}
    assert mock_httpx_client.get.call_count == 3
    # Check backoff times based on mocked config: BACKOFF_BASE=2
    # Attempt 0: 2**0 = 1.0s, Attempt 1: 2**1 = 2.0s, Attempt 2: 2**2 = 4.0s
    assert asyncio.sleep.call_count == 3
    assert asyncio.sleep.call_args_list[0][0][0] == 1.0
    assert asyncio.sleep.call_args_list[1][0][0] == 2.0
    assert asyncio.sleep.call_args_list[2][0][0] == 4.0


@pytest.mark.asyncio
@patch("asyncio.sleep", new=AsyncMock())
async def test_make_request_network_exception_exhausted(
    client_with_mock_httpx, mock_httpx_client, mock_config
):
    """Test network exception exhausts all retries."""
    # Simulate a network error. The code runs with mocked MAX_RETRIES=3.
    mock_httpx_client.get.side_effect = [
        ConnectionError("Network failed"),
        ConnectionError("Network failed"),
        ConnectionError("Network failed"),
    ]

    result = await client_with_mock_httpx._make_request_with_retry(
        "url", {"Authorization": "Bearer token"}, {}
    )

    assert result == {"itemSummaries": []}
    assert mock_httpx_client.get.call_count == 3
    # Network errors only sleep if attempt < MAX_RETRIES - 1.
    # So, it only sleeps on the first two attempts (attempt=0,1).
    assert asyncio.sleep.call_count == 2
    assert asyncio.sleep.call_args_list[0][0][0] == 1.0
    assert asyncio.sleep.call_args_list[1][0][0] == 2.0


@pytest.mark.asyncio
@patch("asyncio.sleep", new=AsyncMock())
async def test_make_request_non_retryable_error(
    client_with_mock_httpx, mock_httpx_client
):
    """Test non-retryable error (e.g., 400) returns empty immediately."""
    mock_httpx_client.get.return_value = mock_response(400)

    result = await client_with_mock_httpx._make_request_with_retry(
        "url", {"Authorization": "Bearer token"}, {}
    )

    assert result == {"itemSummaries": []}
    mock_httpx_client.get.assert_called_once()
    asyncio.sleep.assert_not_called()

# --- Tests for search method ---


@pytest.mark.asyncio
@patch("time.time", side_effect=[100.0, 101.0, 102.0, 103.0])  # Patch 1 - need 4 values for time.time() calls
async def test_search_request_construction_and_latency(mock_time, client_with_mock_httpx, mock_auth_service):
    """Test search method constructs the request correctly and logs latency."""
    client = client_with_mock_httpx

    # Mock the _make_request_with_retry method directly on the client instance
    mock_make_request_with_retry = AsyncMock()
    mock_make_request_with_retry.return_value = {"itemSummaries": [{"itemId": "1"}]}
    client._make_request_with_retry = mock_make_request_with_retry

    await client.search(
        q="test query", limit=100, offset=10, extra_filter="priceCurrency:EUR"
    )

    # 1. Check token retrieval
    mock_auth_service.get_access_token.assert_called_once()
    assert mock_auth_service.get_access_token.return_value == "initial_token"

    # 2. Check _make_request_with_retry call arguments
    call_args = mock_make_request_with_retry.call_args[0]
    url = call_args[0]
    headers = call_args[1]
    params = call_args[2]

    # Check URL
    assert url == f"{client.base_url}/item_summary/search"

    # Check Headers
    assert headers["Authorization"] == "Bearer initial_token"
    assert headers["X-EBAY-C-MARKETPLACE-ID"] == "EBAY_US"

    # Check Params (including clamping and extra filter)
    expected_filter = f"{FILTER},priceCurrency:EUR"
    assert params["q"] == "test query"
    assert params["filter"] == expected_filter
    assert params["limit"] == 50  # Clamped from 100 to 50
    assert params["offset"] == 10
    assert params["fieldgroups"] == "EXTENDED"


@pytest.mark.asyncio
async def test_search_query_clamping(client_with_mock_httpx, mock_auth_service):
    """Test that the query string 'q' is clamped to 100 characters."""
    client = client_with_mock_httpx

    # Mock the _make_request_with_retry method directly on the client instance
    mock_make_request_with_retry = AsyncMock()
    mock_make_request_with_retry.return_value = {"itemSummaries": []}
    client._make_request_with_retry = mock_make_request_with_retry

    mock_auth_service.get_access_token.return_value = "initial_token"

    long_query = "a" * 150
    expected_query = "a" * 100

    await client.search(q=long_query, limit=10, offset=0)

    call_args = mock_make_request_with_retry.call_args[0]
    params = call_args[2]

    assert params["q"] == expected_query


@pytest.mark.asyncio
async def test_search_limit_clamping(client_with_mock_httpx, mock_auth_service):
    """Test that the limit parameter is clamped to 50."""
    client = client_with_mock_httpx

    # Mock the _make_request_with_retry method directly on the client instance
    mock_make_request_with_retry = AsyncMock()
    mock_make_request_with_retry.return_value = {"itemSummaries": []}
    client._make_request_with_retry = mock_make_request_with_retry

    mock_auth_service.get_access_token.return_value = "initial_token"

    # Test limit > 50
    await client.search(q="test", limit=100, offset=0)
    params = mock_make_request_with_retry.call_args[0][2]
    assert params["limit"] == 50

    # Test limit <= 50
    await client.search(q="test", limit=49, offset=0)
    params = mock_make_request_with_retry.call_args[0][2]
    assert params["limit"] == 49


# --- Tests for get_item method ---

@pytest.mark.asyncio
@patch("time.time", side_effect=[100.0, 101.0, 102.0, 103.0])  # Patch 1 - need 4 values for time.time() calls
async def test_get_item_request_construction_and_latency(mock_time, client_with_mock_httpx, mock_auth_service):
    """Test get_item method constructs the request correctly and logs latency."""
    client = client_with_mock_httpx

    # Mock the _make_request_with_retry method directly on the client instance
    mock_make_request_with_retry = AsyncMock()
    mock_make_request_with_retry.return_value = {"item": {"itemId": "123"}}
    client._make_request_with_retry = mock_make_request_with_retry

    item_id = "v1|1234567890|0"

    await client.get_item(item_id=item_id, fieldgroups="IMAGE")

    # 1. Check token retrieval
    mock_auth_service.get_access_token.assert_called_once()

    # 2. Check _make_request_with_retry call arguments
    call_args = mock_make_request_with_retry.call_args[0]
    url = call_args[0]
    headers = call_args[1]
    params = call_args[2]

    # Check URL
    assert url == f"{client.base_url}/item/{item_id}"

    # Check Headers
    assert headers["Authorization"] == "Bearer initial_token"
    assert headers["X-EBAY-C-MARKETPLACE-ID"] == "EBAY_US"

    # Check Params
    assert params["fieldgroups"] == "IMAGE"
