#!/usr/bin/env python3
"""
Test script to validate eBay OAuth 2.0 authentication flow
"""

from common_py.logging_config import configure_logging
import httpx
import aioredis
from services.auth import eBayAuthService
from config_loader import config
import pytest
import asyncio
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))


logger = configure_logging("dropship-product-finder:test_auth_flow")


@pytest.mark.integration
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

    # Verify full scope configuration
    expected_scopes = "https://api.ebay.com/oauth/api_scope"
    if config.EBAY_SCOPES != expected_scopes:
        print(
            f"   ❌ ERROR: Expected full scopes '{expected_scopes}', got '{config.EBAY_SCOPES}'"
        )
        return False

    if not config.EBAY_CLIENT_ID or not config.EBAY_CLIENT_SECRET:
        print("   ❌ ERROR: eBay credentials not properly configured")
        return False

    print("   ✅ Configuration loaded successfully with full scopes")

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

        # Verify that the auth service has the correct scopes
        expected_scopes = "https://api.ebay.com/oauth/api_scope"
        if auth_service.scopes != expected_scopes:
            print(
                f"   ❌ ERROR: Auth service has incorrect scopes: '{auth_service.scopes}'"
            )
            return False
        print("   ✅ Authentication service has correct full scopes")
    except Exception as e:
        print(f"   ❌ Authentication service initialization failed: {e}")
        return False

    # Test 4: Token retrieval
    print("\n4. Testing token retrieval...")
    try:
        start_time = asyncio.get_event_loop().time()
        access_token = await auth_service.get_access_token()
        end_time = asyncio.get_event_loop().time()

        print("   ✅ Token retrieved successfully")
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
            print(
                f"   Stored token length: {len(stored_token.get('access_token', ''))}"
            )
            print(f"   Expires in: {stored_token.get('expires_in', 'N/A')} seconds")
            print(f"   Stored at: {stored_token.get('stored_at', 'N/A')}")
        else:
            print("   ❌ Token not found in Redis")
            return False
    except Exception as e:
        print(f"   ❌ Token storage validation failed: {e}")
        return False

    # Test 6: Verify OAuth request data contains correct scopes
    print("\n6. Testing OAuth request data...")
    try:
        # Mock the HTTP client to capture the request data
        original_post = httpx.AsyncClient.post
        captured_data = {}

        async def mock_post(*args, **kwargs):
            captured_data.update(kwargs.get("data", {}))

            # Create a mock response
            class MockResponse:
                def __init__(self):
                    self.status_code = 200
                    self._json_data = {"access_token": "mock_token", "expires_in": 7200}

                def json(self):
                    return self._json_data

                def raise_for_status(self):
                    pass

            return MockResponse()

        # Patch the post method
        httpx.AsyncClient.post = mock_post

        # Trigger a token refresh to capture the request data
        await auth_service._refresh_token()

        # Restore original method
        httpx.AsyncClient.post = original_post

        # Verify the scopes in the request data
        expected_scopes = "https://api.ebay.com/oauth/api_scope"
        if captured_data.get("scope") == expected_scopes:
            print("   ✅ OAuth request contains correct full scopes")
            print(f"   Request scopes: {captured_data.get('scope')}")
        else:
            print(
                f"   ❌ OAuth request has incorrect scopes: '{captured_data.get('scope')}'"
            )
            print(f"   Expected: {expected_scopes}")
            return False

    except Exception as e:
        print(f"   ❌ OAuth request data test failed: {e}")
        # Restore original method in case of error
        httpx.AsyncClient.post = original_post
        return False

    # Test 7: Token refresh
    print("\n7. Testing token refresh...")
    try:
        start_time = asyncio.get_event_loop().time()
        await auth_service._refresh_token()
        end_time = asyncio.get_event_loop().time()

        print("   ✅ Token refresh successful")
        print(f"   Refresh time: {end_time - start_time:.2f} seconds")

        # Verify new token was stored
        refreshed_token = await auth_service._retrieve_token()
        if refreshed_token:
            print(
                f"   Refreshed token length: {len(refreshed_token.get('access_token', ''))}"
            )
        else:
            print("   ❌ Refreshed token not found in Redis")
            return False

    except Exception as e:
        print(f"   ❌ Token refresh failed: {e}")
        return False

    # Test 8: API call with authentication (skipped due to scope limitations)
    print("\n8. Testing API call with authentication...")
    print(
        "   ⚠️  Skipping API call test - requires additional scopes not available for this application"
    )
    print("   ✅ Authentication flow test completed successfully")

    # Cleanup
    await redis_client.close()
    print("\n=== Test Summary ===")
    print(
        "✅ All tests passed! eBay OAuth 2.0 authentication flow is working correctly."
    )
    return True


if __name__ == "__main__":
    success = asyncio.run(test_ebay_auth_flow())
    sys.exit(0 if success else 1)
