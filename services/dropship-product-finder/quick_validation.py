#!/usr/bin/env python3
"""
Quick validation test for eBay OAuth 2.0 implementation
"""
import asyncio
import sys
import os
from pathlib import Path
import time

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import config
from services.auth import eBayAuthService
from collectors.collectors import EbayProductCollector
import aioredis

async def _test_configuration(results: dict) -> bool:
    print("\n1. Configuration Check...")
    try:
        results["config"] = {
            "ebay_client_id": bool(config.EBAY_CLIENT_ID),
            "ebay_client_secret": bool(config.EBAY_CLIENT_SECRET),
            "ebay_environment": config.EBAY_ENVIRONMENT,
            "ebay_token_url": config.EBAY_TOKEN_URL,
            "redis_url": bool(config.REDIS_URL)
        }
        print(f"   ✅ Configuration loaded")
        print(f"   Environment: {config.EBAY_ENVIRONMENT}")
        print(f"   Token URL: {config.EBAY_TOKEN_URL}")
        return True
    except Exception as e:
        results["config"] = {"error": str(e)}
        print(f"   ❌ Configuration error: {e}")
        return False

async def _test_redis_connection(results: dict) -> bool:
    print("\n2. Redis Connection...")
    try:
        redis_client = aioredis.from_url(config.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        results["redis"] = {"status": "connected"}
        print(f"   ✅ Redis connected")
        await redis_client.close()
        return True
    except Exception as e:
        results["redis"] = {"error": str(e)}
        print(f"   ❌ Redis error: {e}")
        return False

async def _test_authentication_service(results: dict) -> bool:
    print("\n3. Authentication Service...")
    try:
        redis_client = aioredis.from_url(config.REDIS_URL, decode_responses=True)
        auth_service = eBayAuthService(config, redis_client)
        results["auth_service"] = {"status": "initialized"}
        print(f"   ✅ Auth service initialized")
        await redis_client.close()
        return True
    except Exception as e:
        results["auth_service"] = {"error": str(e)}
        print(f"   ❌ Auth service error: {e}")
        return False

async def _test_token_retrieval(results: dict) -> bool:
    print("\n4. Token Retrieval...")
    try:
        redis_client = aioredis.from_url(config.REDIS_URL, decode_responses=True)
        auth_service = eBayAuthService(config, redis_client)
        
        start_time = time.time()
        token = await asyncio.wait_for(auth_service.get_access_token(), timeout=30.0)
        token_time = time.time() - start_time
        
        results["token"] = {
            "status": "retrieved",
            "length": len(token),
            "time": round(token_time, 3)
        }
        print(f"   ✅ Token retrieved ({len(token)} chars, {token_time:.3f}s)")
        await redis_client.close()
        return True
    except asyncio.TimeoutError:
        results["token"] = {"error": "timeout"}
        print(f"   ❌ Token retrieval timed out")
        return False
    except Exception as e:
        results["token"] = {"error": str(e)}
        print(f"   ❌ Token error: {e}")
        return False

async def _test_api_call(results: dict) -> bool:
    print("\n5. Browse API Call...")
    try:
        redis_client = aioredis.from_url(config.REDIS_URL, decode_responses=True)
        auth_service = eBayAuthService(config, redis_client)
        collector = EbayProductCollector("/tmp/test", auth_service)
        
        start_time = time.time()
        products = await asyncio.wait_for(
            collector.collect_products("iphone", 1),  # Use realistic product query
            timeout=30.0
        )
        api_time = time.time() - start_time
        
        results["api"] = {
            "status": "success",
            "products": len(products),
            "time": round(api_time, 3)
        }
        print(f"   ✅ API call successful ({len(products)} products, {api_time:.3f}s)")
        await redis_client.close()
        return True
    except asyncio.TimeoutError:
        results["api"] = {"error": "timeout"}
        print(f"   ❌ API call timed out")
        return False
    except Exception as e:
        results["api"] = {"error": str(e)}
        print(f"   ❌ API error: {e}")
        return False

async def quick_validation():
    """Quick validation of key components"""
    print("=== Quick eBay OAuth Validation ===")
    
    results = {}
    
    config_passed = await _test_configuration(results)
    if not config_passed: return False

    redis_passed = await _test_redis_connection(results)
    if not redis_passed: return False

    auth_service_passed = await _test_authentication_service(results)
    if not auth_service_passed: return False

    token_passed = await _test_token_retrieval(results)
    if not token_passed: return False

    api_passed = await _test_api_call(results)
    if not api_passed: return False
    
    # Summary
    print("\n" + "="*50)
    print("VALIDATION SUMMARY")
    print("="*50)
    
    all_passed = all(
        not isinstance(result, dict) or result.get("status") == "success" or 
        result.get("status") == "retrieved" or result.get("status") == "connected" or
        result.get("status") == "initialized"
        for result in results.values()
    )
    
    if all_passed:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("✅ Configuration: OK")
        print("✅ Redis: OK") 
        print("✅ Auth Service: OK")
        print("✅ Token Retrieval: OK")
        print("✅ Browse API: OK")
        return True
    else:
        print("❌ VALIDATION FAILED")
        for test, result in results.items():
            if isinstance(result, dict) and "error" in result:
                print(f"❌ {test}: {result['error']}")
        return False

if __name__ == "__main__":
    success = asyncio.run(quick_validation())
    sys.exit(0 if success else 1)
