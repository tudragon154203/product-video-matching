#!/usr/bin/env python3
"""
End-to-end test for eBay OAuth 2.0 authentication and product collection
"""

from common_py.logging_config import configure_logging
import redis.asyncio as redis
from services.auth import eBayAuthService
from collectors.ebay_product_collector import EbayProductCollector
from config_loader import config
import asyncio
import pytest
import sys
from pathlib import Path
import json
import time
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))


logger = configure_logging("dropship-product-finder:test_e2e_auth")

pytestmark = pytest.mark.integration

async def test_e2e_flow():
    """Test complete end-to-end flow"""
    print("=== eBay OAuth 2.0 End-to-End Test ===")

    # Initialize components
    redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)
    collector = EbayProductCollector("/tmp/test", redis_client=redis_client)
    auth_service = eBayAuthService(config, redis_client)

    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "tests": {},
        "performance": {},
        "issues": [],
    }

    # Test 1: Authentication Flow
    print("\n1. Testing Authentication Flow...")
    start_time = time.time()

    try:
        # Get token
        token = await auth_service.get_access_token()
        token_time = time.time() - start_time

        # Verify token
        stored_token = await auth_service._retrieve_token()

        results["tests"]["auth"] = {
            "status": "PASS",
            "token_length": len(token),
            "token_retrieval_time": round(token_time, 3),
            "expires_in": stored_token.get("expires_in", "N/A")
            if stored_token
            else "N/A",
            "stored_at": stored_token.get("stored_at", "N/A")
            if stored_token
            else "N/A",
        }

        print("   ✅ Authentication successful")
        print(f"   Token length: {len(token)} characters")
        print(f"   Retrieval time: {token_time:.3f} seconds")

    except Exception as e:
        results["tests"]["auth"] = {"status": "FAIL", "error": str(e)}
        results["issues"].append(f"Authentication failed: {e}")
        print(f"   ❌ Authentication failed: {e}")
        return False

    # Test 2: Token Refresh
    print("\n2. Testing Token Refresh...")
    start_time = time.time()

    try:
        await auth_service._refresh_token()
        refresh_time = time.time() - start_time

        # Verify new token
        new_token = await auth_service.get_access_token()
        new_stored_token = await auth_service._retrieve_token()

        results["tests"]["refresh"] = {
            "status": "PASS",
            "refresh_time": round(refresh_time, 3),
            "new_token_length": len(new_token),
            "new_expires_in": new_stored_token.get("expires_in", "N/A")
            if new_stored_token
            else "N/A",
        }

        print("   ✅ Token refresh successful")
        print(f"   Refresh time: {refresh_time:.3f} seconds")
        print(f"   New token length: {len(new_token)} characters")

    except Exception as e:
        results["tests"]["refresh"] = {"status": "FAIL", "error": str(e)}
        results["issues"].append(f"Token refresh failed: {e}")
        print(f"   ❌ Token refresh failed: {e}")

    # Test 3: Product Collection
    print("\n3. Testing Product Collection...")
    start_time = time.time()

    try:
        # Test with different search queries
        test_queries = ["iphone", "laptop", "headphones"]
        collected_products = []

        for query in test_queries:
            print(f"   Searching for: {query}")
            products = await collector.collect_products(query, 2)
            collected_products.extend(products)
            print(f"   Found {len(products)} products for '{query}'")

            # Small delay to avoid rate limiting
            await asyncio.sleep(1)

        collection_time = time.time() - start_time

        results["tests"]["collection"] = {
            "status": "PASS",
            "total_products": len(collected_products),
            "queries_tested": len(test_queries),
            "collection_time": round(collection_time, 3),
            "products_per_second": round(len(collected_products) / collection_time, 2)
            if collection_time > 0
            else 0,
        }

        print("   ✅ Product collection successful")
        print(f"   Total products collected: {len(collected_products)}")
        print(f"   Collection time: {collection_time:.3f} seconds")

        # Show sample products
        if collected_products:
            print("   Sample products:")
            for i, product in enumerate(collected_products[:3]):
                print(
                    f"     {i + 1}. {product.get('title', 'N/A')} (ID: {product.get('id', 'N/A')})"
                )

    except Exception as e:
        results["tests"]["collection"] = {"status": "FAIL", "error": str(e)}
        results["issues"].append(f"Product collection failed: {e}")
        print(f"   ❌ Product collection failed: {e}")

    # Test 4: Error Handling
    print("\n4. Testing Error Handling...")

    try:
        # Test with invalid query (should handle gracefully)
        invalid_products = await collector.collect_products("", 1)
        results["tests"]["error_handling"] = {
            "status": "PASS",
            "empty_query_result": len(invalid_products),
        }
        print("   ✅ Error handling successful")
        print(f"   Empty query handled gracefully: {len(invalid_products)} results")

    except Exception as e:
        results["tests"]["error_handling"] = {"status": "FAIL", "error": str(e)}
        results["issues"].append(f"Error handling failed: {e}")
        print(f"   ❌ Error handling failed: {e}")

    # Test 5: Performance Metrics
    print("\n5. Performance Validation...")

    try:
        # Measure concurrent token requests
        start_time = time.time()
        concurrent_tasks = [auth_service.get_access_token() for _ in range(3)]
        await asyncio.gather(*concurrent_tasks)
        concurrent_time = time.time() - start_time

        results["tests"]["performance"] = {
            "status": "PASS",
            "concurrent_requests": 3,
            "concurrent_time": round(concurrent_time, 3),
            "avg_time_per_request": round(concurrent_time / 3, 3),
        }

        print("   ✅ Performance test successful")
        print("   Concurrent requests: 3")
        print(f"   Total time: {concurrent_time:.3f} seconds")
        print(f"   Average per request: {concurrent_time / 3:.3f} seconds")

    except Exception as e:
        results["tests"]["performance"] = {"status": "FAIL", "error": str(e)}
        results["issues"].append(f"Performance test failed: {e}")
        print(f"   ❌ Performance test failed: {e}")

    # Test 6: Redis Integration
    print("\n6. Testing Redis Integration...")

    try:
        # Verify token is stored in Redis
        stored_token = await auth_service._retrieve_token()
        if stored_token:
            results["tests"]["redis"] = {
                "status": "PASS",
                "token_stored": True,
                "token_size_bytes": len(json.dumps(stored_token)),
            }
            print("   ✅ Redis integration successful")
            print(f"   Token stored in Redis: {len(json.dumps(stored_token))} bytes")
        else:
            results["tests"]["redis"] = {
                "status": "FAIL",
                "error": "No token found in Redis",
            }
            results["issues"].append("Redis integration failed: No token found")
            print("   ❌ No token found in Redis")

    except Exception as e:
        results["tests"]["redis"] = {"status": "FAIL", "error": str(e)}
        results["issues"].append(f"Redis integration failed: {e}")
        print(f"   ❌ Redis integration failed: {e}")

    # Cleanup
    await redis_client.close()

    # Summary
    print("\n" + "=" * 60)
    print("END-TO-END TEST SUMMARY")
    print("=" * 60)

    passed_tests = sum(
        1 for test in results["tests"].values() if test.get("status") == "PASS"
    )
    total_tests = len(results["tests"])

    print(f"Tests Passed: {passed_tests}/{total_tests}")

    for test_name, test_result in results["tests"].items():
        status = "✅ PASS" if test_result.get("status") == "PASS" else "❌ FAIL"
        print(f"  {test_name}: {status}")

    if results["issues"]:
        print("\nIssues Found:")
        for issue in results["issues"]:
            print(f"  ❌ {issue}")

    # Overall assessment
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! eBay OAuth 2.0 implementation is ready for production.")
        return True
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Review issues above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_e2e_flow())

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"test_results_{timestamp}.json"

    with open(result_file, "w") as f:
        json.dump(
            {
                "config": {
                    "ebay_client_id": config.EBAY_CLIENT_ID,
                    "ebay_environment": config.EBAY_ENVIRONMENT,
                    "ebay_token_url": config.EBAY_TOKEN_URL,
                },
                "results": locals().get("results", {}),
            },
            f,
            indent=2,
        )

    print(f"\nDetailed results saved to: {result_file}")

    sys.exit(0 if success else 1)
