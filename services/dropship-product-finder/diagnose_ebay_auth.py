#!/usr/bin/env python3
"""
Diagnostic script to identify eBay OAuth authentication issues
"""
import asyncio
import sys
import os
import base64
import httpx
from pathlib import Path
import json

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import config

def print_header(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_section(title):
    print(f"\n--- {title} ---")

def test_configuration():
    """Test configuration details"""
    print_header("eBay OAuth Configuration Diagnostics")
    
    print_section("Configuration Details")
    print(f"EBAY_CLIENT_ID: {config.EBAY_CLIENT_ID}")
    print(f"EBAY_CLIENT_SECRET: {'*' * len(config.EBAY_CLIENT_SECRET)}")
    print(f"EBAY_ENVIRONMENT: {config.EBAY_ENVIRONMENT}")
    print(f"EBAY_TOKEN_URL: {config.EBAY_TOKEN_URL}")
    print(f"EBAY_SCOPES: {config.EBAY_SCOPES}")
    
    # Validate configuration
    issues = []
    if not config.EBAY_CLIENT_ID:
        issues.append("❌ EBAY_CLIENT_ID is empty")
    elif len(config.EBAY_CLIENT_ID) < 10:
        issues.append("⚠️  EBAY_CLIENT_ID seems too short")
    
    if not config.EBAY_CLIENT_SECRET:
        issues.append("❌ EBAY_CLIENT_SECRET is empty")
    elif len(config.EBAY_CLIENT_SECRET) < 10:
        issues.append("⚠️  EBAY_CLIENT_SECRET seems too short")
    
    if config.EBAY_ENVIRONMENT not in ['sandbox', 'production']:
        issues.append(f"⚠️  EBAY_ENVIRONMENT '{config.EBAY_ENVIRONMENT}' is not 'sandbox' or 'production'")
    
    if 'sandbox' in config.EBAY_TOKEN_URL.lower():
        print("✅ Token URL appears to be for sandbox environment")
    else:
        issues.append("⚠️  Token URL doesn't appear to be for sandbox environment")
    
    if 'ebay.com/oauth/api_scope' in config.EBAY_SCOPES:
        print("✅ Scopes appear to be standard eBay OAuth scopes")
    else:
        issues.append("⚠️  Scopes don't appear to be standard eBay OAuth scopes")
    
    if issues:
        print_section("Configuration Issues Found")
        for issue in issues:
            print(issue)
    else:
        print_section("Configuration appears valid")
    
    return len(issues) == 0

def test_basic_auth_encoding():
    """Test basic authentication encoding"""
    print_section("Basic Authentication Encoding Test")
    
    try:
        credentials = f"{config.EBAY_CLIENT_ID}:{config.EBAY_CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        print(f"Credentials: {credentials[:20]}...")
        print(f"Encoded: {encoded_credentials[:30]}...")
        
        # Test decoding
        decoded = base64.b64decode(encoded_credentials).decode()
        print(f"Decoded: {decoded[:20]}...")
        
        if decoded == credentials:
            print("✅ Basic auth encoding/decoding successful")
            return True
        else:
            print("❌ Basic auth encoding/decoding failed")
            return False
            
    except Exception as e:
        print(f"❌ Basic auth encoding test failed: {e}")
        return False

async def _make_token_request(url: str, headers: dict, data: dict, timeout: float = 30.0) -> httpx.Response:
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await client.post(url, headers=headers, data=data)

async def _validate_token_response(response: httpx.Response) -> bool:
    print(f"Response Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print("✅ Token request successful!")
        token_data = response.json()
        print(f"Token Data: {json.dumps(token_data, indent=2)}")
        
        if 'access_token' in token_data:
            print(f"✅ Access token received: {token_data['access_token'][:20]}...")
            if 'expires_in' in token_data:
                print(f"✅ Token expires in: {token_data['expires_in']} seconds")
            return True
        else:
            print("❌ No access_token in response")
            return False
            
    elif response.status_code == 401:
        print("❌ 401 Unauthorized - Authentication failed")
        try:
            error_data = response.json()
            print(f"Error Details: {json.dumps(error_data, indent=2)}")
        except:
            print(f"Error Response: {response.text}")
        return False
        
    elif response.status_code == 400:
        print("❌ 400 Bad Request - Invalid request")
        try:
            error_data = response.json()
            print(f"Error Details: {json.dumps(error_data, indent=2)}")
        except:
            print(f"Error Response: {response.text}")
        return False
        
    else:
        print(f"❌ Unexpected status code: {response.status_code}")
        print(f"Response: {response.text}")
        return False

async def test_ebay_token_request():
    """Test eBay token request with detailed logging"""
    print_section("eBay Token Request Test")
    
    try:
        credentials = f"{config.EBAY_CLIENT_ID}:{config.EBAY_CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}"
        }
        
        data = {
            "grant_type": "client_credentials",
            "scope": config.EBAY_SCOPES
        }
        
        print(f"Request URL: {config.EBAY_TOKEN_URL}")
        print(f"Request Headers: {json.dumps(headers, indent=2)}")
        print(f"Request Data: {json.dumps(data, indent=2)}")
        
        print("\nMaking request...")
        response = await _make_token_request(config.EBAY_TOKEN_URL, headers, data)
        return await _validate_token_response(response)
            
    except httpx.TimeoutException:
        print("❌ Request timed out")
        return False
    except httpx.ConnectError as e:
        print(f"❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def _test_single_endpoint(url: str, headers: dict, data: dict) -> bool:
    print(f"\nTesting: {url}")
    try:
        response = await _make_token_request(url, headers, data, timeout=10.0)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ SUCCESS!")
            return True
        elif response.status_code == 401:
            print("  ❌ 401 Unauthorized")
        else:
            print(f"  ❌ {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    return False

async def test_alternative_endpoints():
    """Test alternative eBay OAuth endpoints"""
    print_section("Testing Alternative eBay OAuth Endpoints")
    
    alternative_urls = [
        "https://api.sandbox.ebay.com/identity/v1/oauth2/token",
        "https://api.ebay.com/identity/v1/oauth2/token",
        "https://auth.sandbox.ebay.com/identity/v1/oauth2/token",
        "https://auth.ebay.com/identity/v1/oauth2/token"
    ]
    
    credentials = f"{config.EBAY_CLIENT_ID}:{config.EBAY_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    data = {
        "grant_type": "client_credentials",
        "scope": config.EBAY_SCOPES
    }
    
    for url in alternative_urls:
        if await _test_single_endpoint(url, headers, data):
            return True
    
    return False

async def main():
    """Run all diagnostic tests"""
    print_header("eBay OAuth Authentication Diagnostics")
    
    # Test 1: Configuration
    config_valid = test_configuration()
    
    # Test 2: Basic auth encoding
    auth_valid = test_basic_auth_encoding()
    
    # Test 3: Token request
    token_valid = await test_ebay_token_request()
    
    # Test 4: Alternative endpoints (if main request failed)
    if not token_valid:
        print_section("\nTesting alternative endpoints since main request failed...")
        alt_valid = await test_alternative_endpoints()
    else:
        alt_valid = True
    
    # Summary
    print_header("Diagnostic Summary")
    print(f"Configuration Valid: {'✅' if config_valid else '❌'}")
    print(f"Basic Auth Valid: {'✅' if auth_valid else '❌'}")
    print(f"Token Request Valid: {'✅' if token_valid else '❌'}")
    print(f"Alternative Endpoints Valid: {'✅' if alt_valid else '❌'}")
    
    if token_valid or alt_valid:
        print("\n🎉 eBay OAuth authentication is working!")
        return True
    else:
        print("\n❌ eBay OAuth authentication has issues that need to be resolved.")
        print("\nRecommended actions:")
        print("1. Verify eBay sandbox credentials are valid and not expired")
        print("2. Check if the application is properly registered in eBay Developer Portal")
        print("3. Ensure the application has the correct OAuth scopes configured")
        print("4. Try generating new sandbox credentials")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
