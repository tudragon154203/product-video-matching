"""
Unit tests for eBay authentication service with Redis token management.
"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import asyncio

from dropship_product_finder.services.auth import eBayAuthService
from dropship_product_finder.config_loader import DropshipProductFinderConfig


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
            "stored_at": datetime.utcnow().isoformat()
        }
        mock_redis.get.return_value = json.dumps(cached_token)
        
        # Mock token validation
        with patch.object(auth_service, '_is_token_valid', return_value=True):
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
            "stored_at": datetime.utcnow().isoformat()
        }
        
        with patch.object(auth_service, '_refresh_token') as mock_refresh:
            mock_refresh.return_value = None
            with patch.object(auth_service, '_retrieve_token') as mock_retrieve:
                mock_retrieve.return_value = new_token
                
                token = await auth_service.get_access_token()
                
                assert token == "new_token_456"
                mock_refresh.assert_called_once()
                mock_redis.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, auth_service, mock_redis):
        """Test successful token refresh"""
        # Mock HTTP client response
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "access_token": "refreshed_token_789",
            "expires_in": 7200
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            
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
        
        # Mock HTTP client error
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.reason_phrase = "Unauthorized"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = HTTPStatusError(
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
            "token_type": "Bearer"
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
        token_data = {
            "access_token": "retrieved_token",
            "expires_in": 7200
        }
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
            "stored_at": (datetime.utcnow() - timedelta(seconds=1000)).isoformat()
        }
        
        result = auth_service._is_token_valid(token_data)
        
        assert result is True
    
    def test_is_token_expired_token(self, auth_service):
        """Test token validation for expired token"""
        token_data = {
            "access_token": "expired_token",
            "expires_in": 7200,
            "stored_at": (datetime.utcnow() - timedelta(seconds=7000)).isoformat()  # Expired
        }
        
        result = auth_service._is_token_valid(token_data)
        
        assert result is False
    
    def test_is_token_invalid_format(self, auth_service):
        """Test token validation with invalid format"""
        token_data = {
            "access_token": "invalid_token"
            # Missing expires_in and stored_at
        }
        
        result = auth_service._is_token_valid(token_data)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, auth_service, mock_redis):
        """Test rate limiting functionality"""
        # Mock current time to simulate fast consecutive calls
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.time.side_effect = [1000.0, 1000.5]  # 0.5 second apart
            
            # First call should not sleep
            await auth_service._enforce_rate_limit()
            
            # Second call should sleep for remaining time
            with patch('asyncio.sleep') as mock_sleep:
                await auth_service._enforce_rate_limit()
                mock_sleep.assert_called_once_with(0.5)
    
    @pytest.mark.asyncio
    async def test_enforce_rate_limit_sufficient_interval(self, auth_service, mock_redis):
        """Test rate limiting when sufficient time has passed"""
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.time.side_effect = [1000.0, 1002.0]  # 2 seconds apart
            
            with patch('asyncio.sleep') as mock_sleep:
                await auth_service._enforce_rate_limit()
                mock_sleep.assert_not_called()