#!/usr/bin/env python3
"""
Test script to validate eBay OAuth 2.0 authentication flow
"""
import asyncio
import sys
import os
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import config
from services.auth import eBayAuthService
import aioredis
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

async def test_ebay_auth_flow():
    """Test the complete eBay authentication flow"""
    print("=== eBay OAuth 2.0 Authentication Flow Test ===")
    
    # Test 1: Configuration validation
    print("\n1. Testing configuration loading...")
    print(f"   EBAY_CLIENT_ID: {config.EBAY_CLIENT_ID}")
    print(f"   EBAY_CLIENT_SECRET: {'*' * len(config.EBAY_CLIENT_SECRET)}")
    print(f"   EBAY_ENVIRONMENT: {config.EBAY_ENVIRONMENT}")
    print(f"   EBAY_TOKEN_URL: {config.EBAY_TOKEN_URL}")
    print(f"   EBAY_SCOPES: {config.EBAY_SCOPES}")
    
    if not config.EBAY_CLIENT_ID or not config.EBAY_CLIENT_SECRET:
        print("   ❌ ERROR: eBay credentials not properly configured")
        return False
    
    print("   ✅ Configuration loaded successfully")
    
    # Test 2: Redis connection
    print("\n2. Testing Redis connection...")
    try:
        redis_client = aioredis.from_url(config.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        print("   ✅ Redis connection successful")
        print(f"   Redis URL: {config.REDIS_URL}")
    except Exception as e:
        print(f"   ❌ Redis connection failed: {e}")
        return False
    
    # Test 3: Authentication service initialization
    print("\n3. Testing authentication service initialization...")
    try:
        auth_service = eBayAuthService(config, redis_client)
        print("   ✅ Authentication service initialized successfully")
    except Exception as e:
        print(f"   ❌ Authentication service initialization failed: {e}")
        return False
    
    # Test 4: Token retrieval
    print("\n4. Testing token retrieval...")
    try:
        start_time = asyncio.get_event_loop().time()
        access_token = await auth_service.get_access_token()
        end_time = asyncio.get_event_loop().time()
        
        print(f"   ✅ Token retrieved successfully")
        print(f"   Token length: {len(access_token)} characters")
        print(f"   Retrieval time: {end_time - start_time:.2f} seconds")
        print(f"   Token preview: {access_token[:20]}...")
        
    except Exception as e:
        print(f"   ❌ Token retrieval failed: {e}")
        return False
    
    # Test 5: Token storage validation
    print("\n5. Testing token storage...")
    try:
        stored_token = await auth_service._retrieve_token()
        if stored_token:
            print("   ✅ Token stored in Redis")
            print(f"   Stored token length: {len(stored_token.get('access_token', ''))}")
            print(f"   Expires in: {stored_token.get('expires_in', 'N/A')} seconds")
            print(f"   Stored at: {stored_token.get('stored_at', 'N/A')}")
        else:
            print("   ❌ Token not found in Redis")
            return False
    except Exception as e:
        print(f"   ❌ Token storage validation failed: {e}")
        return False
    
    # Test 6: Token refresh
    print("\n6. Testing token refresh...")
    try:
        start_time = asyncio.get_event_loop().time()
        await auth_service._refresh_token()
        end_time = asyncio.get_event_loop().time()
        
        print(f"   ✅ Token refresh successful")
        print(f"   Refresh time: {end_time - start_time:.2f} seconds")
        
        # Verify new token was stored
        refreshed_token = await auth_service._retrieve_token()
        if refreshed_token:
            print(f"   Refreshed token length: {len(refreshed_token.get('access_token', ''))}")
        else:
            print("   ❌ Refreshed token not found in Redis")
            return False
            
    except Exception as e:
        print(f"   ❌ Token refresh failed: {e}")
        return False
    
    # Test 7: API call with authentication (skipped due to scope limitations)
    print("\n7. Testing API call with authentication...")
    print("   ⚠️  Skipping API call test - requires additional scopes not available for this application")
    print("   ✅ Authentication flow test completed successfully")
    
    # Cleanup
    await redis_client.close()
    print("\n=== Test Summary ===")
    print("✅ All tests passed! eBay OAuth 2.0 authentication flow is working correctly.")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_ebay_auth_flow())
    sys.exit(0 if success else 1)