#!/usr/bin/env python3
"""
Test script to validate eBay Browse API with OAuth token
"""
import asyncio
import sys
import os
import base64
from pathlib import Path
import httpx
import json

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

async def test_browse_api():
    """Test eBay Browse API with different approaches"""
    print("=== eBay Browse API Test ===")
    
    # Initialize Redis and Auth service
    redis_client = aioredis.from_url(config.REDIS_URL, decode_responses=True)
    auth_service = eBayAuthService(config, redis_client)
    
    # Test 1: Get fresh token
    print("\n1. Getting fresh access token...")
    access_token = await auth_service.get_access_token()
    print(f"   Token: {access_token[:50]}...")
    
    # Test 2: Test Browse API with different headers
    print("\n2. Testing Browse API with different header formats...")
    
    test_headers = [
        {
            "name": "Standard Bearer",
            "headers": {"Authorization": f"Bearer {access_token}"}
        },
        {
            "name": "Bearer with quotes",
            "headers": {"Authorization": f'Bearer "{access_token}"'}
        },
        {
            "name": "Basic auth with token",
            "headers": {"Authorization": f"Basic {access_token}"}
        }
    ]
    
    base_url = "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search"
    test_params = {
        "q": "iphone",
        "limit": 1
    }
    
    for header_test in test_headers:
        print(f"\n   Testing: {header_test['name']}")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(base_url, headers=header_test['headers'], params=test_params)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("itemSummaries", [])
                    print(f"   ✅ SUCCESS! Found {len(items)} items")
                    print(f"   Response preview: {json.dumps(data, indent=2)[:200]}...")
                    return True
                elif response.status_code == 401:
                    error_data = response.json()
                    print(f"   ❌ 401 Unauthorized: {error_data.get('errors', [{}])[0].get('message', 'Unknown error')}")
                else:
                    print(f"   ❌ {response.status_code}: {response.text[:200]}...")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Test 3: Test with different scopes
    print("\n3. Testing with different OAuth scopes...")
    
    # Get token with specific Browse API scope
    try:
        # Manually request token with browse scope
        credentials = f"{config.EBAY_CLIENT_ID}:{config.EBAY_CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}"
        }
        
        # Try different scope combinations
        scope_variants = [
            "https://api.ebay.com/oauth/api_scope",
            "https://api.ebay.com/oauth/api_scope/buy.browse",
            "https://api.ebay.com/oauth/api_scope/buy.item_summary.readonly",
            "https://api.ebay.com/oauth/api_scope/buy.item_search.readonly"
        ]
        
        for scope in scope_variants:
            print(f"\n   Testing scope: {scope}")
            data = {
                "grant_type": "client_credentials",
                "scope": scope
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(config.EBAY_TOKEN_URL, headers=headers, data=data)
                
                if response.status_code == 200:
                    token_data = response.json()
                    browse_token = token_data.get("access_token")
                    
                    # Test with browse token
                    browse_headers = {"Authorization": f"Bearer {browse_token}"}
                    response = await client.get(base_url, headers=browse_headers, params=test_params)
                    
                    print(f"   Token test status: {response.status_code}")
                    if response.status_code == 200:
                        print(f"   ✅ SUCCESS with scope: {scope}")
                        return True
                    else:
                        print(f"   ❌ Failed with scope: {scope}")
                else:
                    print(f"   ❌ Token request failed for scope: {scope}")
                    
    except Exception as e:
        print(f"   ❌ Scope test error: {e}")
    
    # Test 4: Test API endpoint validation
    print("\n4. Testing API endpoint validation...")
    
    # Check if we can access the API at all
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test without authentication
            response = await client.get(base_url, params={"q": "test", "limit": 1})
            print(f"   No auth status: {response.status_code}")
            
            if response.status_code == 401:
                print("   ✅ API properly requires authentication")
            else:
                print(f"   ⚠️  Unexpected response without auth: {response.status_code}")
                
    except Exception as e:
        print(f"   ❌ Endpoint validation error: {e}")
    
    await redis_client.close()
    return False

if __name__ == "__main__":
    success = asyncio.run(test_browse_api())
    if success:
        print("\n🎉 eBay Browse API test successful!")
    else:
        print("\n❌ eBay Browse API test failed.")
        print("\nPossible solutions:")
        print("1. Check if the OAuth token has the required scopes for Browse API")
        print("2. Verify the eBay application has Browse API permissions enabled")
        print("3. Check if the sandbox application is properly configured")
    sys.exit(0 if success else 1)