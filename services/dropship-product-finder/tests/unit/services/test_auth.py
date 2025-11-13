"""
Unit tests for eBay authentication service with Redis token management.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config_loader import DropshipProductFinderConfig
from services.auth import eBayAuthService

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    config = MagicMock(spec=DropshipProductFinderConfig)
    config.EBAY_CLIENT_ID = "test_client_id"
    config.EBAY_CLIENT_SECRET = "test_client_secret"
    config.EBAY_TOKEN_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    config.EBAY_SCOPES = "https://api.ebay.com/oauth/api_scope"
    return config


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    redis = AsyncMock()
    return redis


@pytest.fixture
def auth_service(mock_config, mock_redis):
    """Create eBay auth service with mocked dependencies"""
    return eBayAuthService(mock_config, mock_redis)


class TesteBayAuthService:
    """Test cases for eBay authentication service"""

    @pytest.mark.asyncio
    async def test_get_access_token_from_cache(self, auth_service, mock_redis):
        """Test getting access token from Redis cache"""
        # Mock cached token data
        cached_token = {
            "access_token": "cached_token_123",
            "expires_in": 7200,
            "stored_at": datetime.utcnow().isoformat(),
        }
        mock_redis.get.return_value = json.dumps(cached_token)

        # Mock token validation
        with patch.object(auth_service, "_is_token_valid", return_value=True):
            token = await auth_service.get_access_token()

            assert token == "cached_token_123"
            mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_access_token_refresh_needed(self, auth_service, mock_redis):
        """Test token refresh when cached token is invalid"""
        # Mock no cached token
        mock_redis.get.return_value = None

        # Mock successful token refresh
        new_token = {
            "access_token": "new_token_456",
            "expires_in": 7200,
            "stored_at": datetime.utcnow().isoformat(),
        }

        with patch.object(auth_service, "_refresh_token") as mock_refresh:
            mock_refresh.return_value = None
            with patch.object(auth_service, "_retrieve_token") as mock_retrieve:
                # First call returns None (no cached token). Second call returns the
                # new token.
                mock_retrieve.side_effect = [None, new_token]

                token = await auth_service.get_access_token()

                assert token == "new_token_456"
                mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, auth_service, mock_redis):
        """Test successful token refresh"""
        # Mock API client response
        with patch.object(
            auth_service.api_client, "request_access_token"
        ) as mock_request:
            mock_request.return_value = {
                "access_token": "refreshed_token_789",
                "expires_in": 7200,
            }

            await auth_service._refresh_token()

            # Verify token was stored in Redis
            mock_redis.setex.assert_called_once()
            args = mock_redis.setex.call_args
            assert args[0][0] == auth_service.redis_key  # Redis key
            assert args[0][1] > 0  # TTL
            assert "refreshed_token_789" in args[0][2]  # Token data

    @pytest.mark.asyncio
    async def test_refresh_token_http_error(self, auth_service, mock_redis):
        """Test token refresh with HTTP error"""
        from httpx import HTTPStatusError

        # Mock API client error
        with patch.object(
            auth_service.api_client, "request_access_token"
        ) as mock_request:
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_response.reason_phrase = "Unauthorized"
            mock_request.side_effect = HTTPStatusError(
                "401 Unauthorized", request=AsyncMock(), response=mock_response
            )

            with pytest.raises(HTTPStatusError):
                await auth_service._refresh_token()

            # Verify token was not stored
            mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_token(self, auth_service, mock_redis):
        """Test token storage in Redis"""
        token_data = {
            "access_token": "test_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        await auth_service._store_token(token_data)

        # Verify Redis call
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args
        assert args[0][0] == auth_service.redis_key
        assert args[0][1] == 3300  # 3600 - 300 (buffer)
        assert "test_token" in args[0][2]

    @pytest.mark.asyncio
    async def test_retrieve_token_success(self, auth_service, mock_redis):
        """Test successful token retrieval from Redis"""
        token_data = {"access_token": "retrieved_token", "expires_in": 7200}
        mock_redis.get.return_value = json.dumps(token_data)

        result = await auth_service._retrieve_token()

        assert result == token_data
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_token_no_data(self, auth_service, mock_redis):
        """Test token retrieval when no data exists"""
        mock_redis.get.return_value = None

        result = await auth_service._retrieve_token()

        assert result is None

    def test_is_token_valid_valid_token(self, auth_service):
        """Test token validation for valid token"""
        token_data = {
            "access_token": "valid_token",
            "expires_in": 7200,
            "stored_at": (datetime.utcnow() - timedelta(seconds=1000)).isoformat(),
        }

        result = auth_service._is_token_valid(token_data)

        assert result is True

    def test_is_token_expired_token(self, auth_service):
        """Test token validation for expired token"""
        token_data = {
            "access_token": "expired_token",
            "expires_in": 7200,
            "stored_at": (
                datetime.utcnow() - timedelta(seconds=7000)
            ).isoformat(),  # Expired
        }

        result = auth_service._is_token_valid(token_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_redis_returning_valid_token(self, auth_service, mock_redis):
        """Test Redis returning a valid, unexpired token"""
        # Mock cached token data that is still valid
        cached_token = {
            "access_token": "valid_cached_token",
            "expires_in": 7200,
            "stored_at": (datetime.utcnow() - timedelta(seconds=1000)).isoformat(),
        }
        mock_redis.get.return_value = json.dumps(cached_token)

        # Mock token validation to return True
        with patch.object(auth_service, "_is_token_valid", return_value=True):
            token = await auth_service.get_access_token()

            assert token == "valid_cached_token"
            mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_returning_expired_token(self, auth_service, mock_redis):
        """Test Redis returning a token that has passed its expires_in timestamp (with 5-minute buffer)"""
        # Mock cached token data that is expired (accounting for 5-minute buffer)
        cached_token = {
            "access_token": "expired_cached_token",
            "expires_in": 7200,
            "stored_at": (datetime.utcnow() - timedelta(seconds=7000)).isoformat(),  # Expired
        }
        mock_redis.get.return_value = json.dumps(cached_token)

        # Mock token validation to return False
        with patch.object(auth_service, "_is_token_valid", return_value=False):
            # Mock token refresh
            new_token = {
                "access_token": "new_refreshed_token",
                "expires_in": 7200,
                "stored_at": datetime.utcnow().isoformat(),
            }

            with patch.object(auth_service, "_refresh_token") as mock_refresh:
                mock_refresh.return_value = None
                with patch.object(auth_service, "_retrieve_token") as mock_retrieve:
                    # First call returns expired token, second call returns new token
                    mock_retrieve.side_effect = [cached_token, new_token]

                    token = await auth_service.get_access_token()

                    assert token == "new_refreshed_token"
                    # The mock_redis.get should be called once by the first _retrieve_token call
                    # But since we're mocking _retrieve_token, the actual Redis.get won't be called
                    # Let's check that _retrieve_token was called instead
                    mock_retrieve.assert_called()
                    mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_get_raising_exception(self, auth_service, mock_redis):
        """Test Redis.get raising an exception"""
        # Mock Redis.get to raise an exception
        mock_redis.get.side_effect = Exception("Redis connection error")

        # Test that the exception is handled gracefully and returns None
        result = await auth_service._retrieve_token()

        assert result is None
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_get_raising_connection_error(self, auth_service, mock_redis):
        """Test Redis.get raising a ConnectionError"""
        # Mock Redis.get to raise a ConnectionError
        mock_redis.get.side_effect = Exception("Redis connection error")

        # Test that the exception is handled gracefully and returns None
        result = await auth_service._retrieve_token()

        assert result is None
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_token_warning_when_redis_missing(self, auth_service, mock_redis):
        """Test _store_token function handles missing Redis gracefully"""
        # Set Redis client to None
        auth_service.redis = None

        token_data = {
            "access_token": "test_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        # Call _store_token and check that it doesn't raise an exception
        await auth_service._store_token(token_data)

        # Verify Redis.setex was not called
        mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_token_warning_when_redis_setex_fails(self, auth_service, mock_redis):
        """Test _store_token function raises exception when Redis.setex fails"""
        # Mock Redis.setex to raise an exception
        mock_redis.setex.side_effect = Exception("Redis setex failed")

        token_data = {
            "access_token": "test_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        # Call _store_token and check that exception is raised
        with pytest.raises(Exception, match="Redis setex failed"):
            await auth_service._store_token(token_data)

        # Verify Redis.setex was called
        mock_redis.setex.assert_called_once()

    def test_is_token_invalid_format(self, auth_service):
        """Test token validation with invalid format"""
        token_data = {
            "access_token": "invalid_token"
            # Missing expires_in and stored_at
        }

        result = auth_service._is_token_valid(token_data)

        assert result is False
