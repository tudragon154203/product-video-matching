"""
eBay OAuth 2.0 authentication service with Redis token storage.
"""
import json
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from common_py.logging_config import configure_logging
from .ebay_auth_api_client import EbayAuthAPIClient

logger = configure_logging("dropship-product-finder")


class eBayAuthService:
    """Service for managing eBay OAuth 2.0 authentication with Redis token storage"""
    
    def __init__(self, config, redis_client):
        self.client_id = config.EBAY_CLIENT_ID
        self.client_secret = config.EBAY_CLIENT_SECRET
        self.token_url = config.EBAY_TOKEN_URL
        self.scopes = config.EBAY_SCOPES
        self.redis = redis_client
        self.redis_key = "ebay:access_token"
        self.api_client = EbayAuthAPIClient(self.client_id, self.client_secret, self.token_url, self.scopes)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # seconds
        
    async def get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary"""
        # Check Redis first
        token_data = await self._retrieve_token()
        
        if token_data and self._is_token_valid(token_data):
            logger.debug("Using cached eBay token")
            return token_data["access_token"]
        
        # Token not valid or not found, refresh it
        logger.info("Refreshing eBay access token")
        await self._refresh_token()
        
        # Get the newly stored token
        token_data = await self._retrieve_token()
        if token_data:
            return token_data["access_token"]
        
        raise RuntimeError("Failed to obtain eBay access token")
    
    async def _refresh_token(self) -> None:
        """Refresh the access token from eBay"""
        # Rate limiting
        await self._enforce_rate_limit()
        
        try:
            token_data = await self.api_client.request_access_token()
            await self._store_token(token_data)
            logger.info("Successfully refreshed eBay token")
                
        except Exception as e:
            logger.error("Error refreshing eBay token", error=str(e))
            raise
    
    async def _store_token(self, token_data: Dict[str, Any]) -> None:
        """Store token data in Redis with expiration"""
        try:
            expires_in = token_data.get("expires_in", 7200)  # Default 2 hours
            # Store with 5-minute buffer to ensure token is still valid
            ttl = expires_in - 300
            
            # Add timestamp for tracking
            token_data["stored_at"] = datetime.utcnow().isoformat()
            
            await self.redis.setex(
                self.redis_key,
                ttl,
                json.dumps(token_data)
            )
            
            logger.debug("Token stored in Redis", ttl=ttl)
            
        except Exception as e:
            logger.error("Failed to store token in Redis", error=str(e))
            raise
    
    async def _retrieve_token(self) -> Optional[Dict[str, Any]]:
        """Retrieve token data from Redis"""
        try:
            token_json = await self.redis.get(self.redis_key)
            if token_json:
                return json.loads(token_json)
            return None
            
        except Exception as e:
            logger.error("Failed to retrieve token from Redis", error=str(e))
            return None
    
    def _is_token_valid(self, token_data: Dict[str, Any]) -> bool:
        """Check if token is still valid"""
        try:
            expires_in = token_data.get("expires_in", 7200)
            stored_at_str = token_data.get("stored_at")
            
            if not stored_at_str:
                logger.debug("Token validation failed: no stored_at timestamp")
                return False
                
            stored_at = datetime.fromisoformat(stored_at_str)
            expiration_time = stored_at + timedelta(seconds=expires_in - 300)  # 5-minute buffer
            current_time = datetime.utcnow()
            
            # Debug logging
            logger.debug("Token validation details",
                        stored_at=stored_at.isoformat(),
                        current_time=current_time.isoformat(),
                        expiration_time=expiration_time.isoformat(),
                        expires_in=expires_in,
                        time_until_expiry=(expiration_time - current_time).total_seconds(),
                        is_valid=current_time < expiration_time)
            
            is_valid = current_time < expiration_time
            
            if not is_valid:
                logger.warning("Token expired",
                              stored_at=stored_at.isoformat(),
                              current_time=current_time.isoformat(),
                              expiration_time=expiration_time.isoformat(),
                              time_until_expiry=(expiration_time - current_time).total_seconds())
            
            return is_valid
            
        except Exception as e:
            logger.error("Error validating token", error=str(e))
            return False
    
    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting to avoid hitting eBay API limits"""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug("Rate limiting, sleeping", sleep_time=sleep_time)
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def close(self) -> None:
        """Clean up resources"""
        # Redis connection is managed externally
        pass