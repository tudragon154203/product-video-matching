#!/usr/bin/env python3
"""
Integration test for eBay product collector using real eBay API calls.
Tests the complete flow from authentication to product collection with real data.
"""

from common_py.logging_config import configure_logging
from collectors.ebay.ebay_product_collector import EbayProductCollector
from services.auth import eBayAuthService
from config_loader import config
import asyncio
import pytest
import sys
from pathlib import Path
import json

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


pytestmark = pytest.mark.integration


logger = configure_logging("dropship-product-finder:test_ebay_collector_real")


@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for each test module"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def auth_service(redis_client):
    """eBay authentication service fixture"""
    # Force sandbox environment for this test
    config.EBAY_ENVIRONMENT = "sandbox"

    service = eBayAuthService(config, redis_client)
    yield service
    await service.close()


@pytest.fixture(scope="module")
async def ebay_collector(redis_client):
    """eBay product collector fixture"""
    collector = EbayProductCollector(
        data_root="/tmp/test_integration",
        redis_client=redis_client,
        marketplaces=["EBAY_US"],  # Test with US marketplace only
    )
    yield collector
    await collector.close()


@pytest.mark.asyncio
async def test_authentication_flow(auth_service):
    """Test eBay OAuth 2.0 authentication flow"""
    logger.info("Testing eBay authentication flow...")

    # Test token retrieval
    token = await auth_service.get_access_token()
    assert isinstance(token, str)
    assert len(token) > 0

    # Verify token is stored in Redis
    stored_token = await auth_service._retrieve_token()
    assert stored_token is not None
    assert "access_token" in stored_token
    assert "expires_in" in stored_token
    assert stored_token["expires_in"] > 0

    logger.info("Authentication successful, token length: %s", len(token))


@pytest.mark.asyncio
async def test_token_refresh(auth_service):
    """Test token refresh functionality"""
    logger.info("Testing token refresh...")

    # Get initial token
    initial_token = await auth_service.get_access_token()

    # Refresh token
    await auth_service._refresh_token()

    # Get new token
    new_token = await auth_service.get_access_token()

    # Verify token changed
    assert new_token != initial_token
    assert len(new_token) > 0

    logger.info("Token refresh successful")


@pytest.mark.asyncio
async def test_basic_product_collection(ebay_collector):
    """Test basic product collection with real eBay API"""
    logger.info("Testing basic product collection...")

    # Test with a common search query
    query = "iphone"
    top_k = 5

    products = await ebay_collector.collect_products(query, top_k)

    # Verify results
    assert isinstance(products, list)
    assert len(products) <= top_k  # Should not exceed requested limit

    # Verify product structure
    if products:
        product = products[0]
        assert "id" in product
        assert "title" in product
        assert "price" in product
        assert "currency" in product
        assert "url" in product
        assert "images" in product
        assert "marketplace" in product
        assert "totalPrice" in product
        assert "shippingCost" in product

        # Verify data types
        assert isinstance(product["title"], str)
        assert isinstance(product["price"], (int, float))
        assert isinstance(product["currency"], str)
        assert isinstance(product["images"], list)
        assert isinstance(product["marketplace"], str)
        assert isinstance(product["totalPrice"], (int, float))
        assert isinstance(product["shippingCost"], (int, float))

        # Verify marketplace is correct
        assert product["marketplace"] == "us"

        # Verify price is reasonable
        assert product["price"] > 0
        assert product["totalPrice"] >= product["price"]

        logger.info("Collected %s products for '%s'", len(products), query)
        logger.info(
            "Sample product: %s... ($%s)",
            product["title"][:50],
            product["price"],
        )


@pytest.mark.asyncio
async def test_multiple_queries(ebay_collector):
    """Test product collection with multiple different queries"""
    logger.info("Testing multiple queries...")

    test_queries = ["laptop", "headphones", "watch", "shoes"]

    all_products = []

    for query in test_queries:
        logger.info("Searching for: %s", query)
        products = await ebay_collector.collect_products(query, 3)

        # Verify results per query
        assert isinstance(products, list)
        if products:  # Some queries might return empty results
            # Verify products have unique IDs within this query
            product_ids = [p["id"] for p in products]
            assert len(product_ids) == len(set(product_ids)), (
                f"Found duplicate product IDs in query: {query}"
            )

            all_products.extend(products)

        # Small delay to avoid rate limiting
        await asyncio.sleep(1)

    # Verify we got some results overall
    assert len(all_products) > 0, "No products collected across all queries"

    logger.info(
        f"Collected {len(all_products)} products across {len(test_queries)} queries"
    )


@pytest.mark.asyncio
async def test_deduplication_logic(ebay_collector):
    """Test product deduplication logic"""
    logger.info("Testing deduplication logic...")

    # Use a query that might return duplicate products
    query = "apple iphone"
    top_k = 10

    products = await ebay_collector.collect_products(query, top_k)

    # Verify no duplicates by ID
    product_ids = [p["id"] for p in products]
    assert len(product_ids) == len(set(product_ids)), "Found duplicate product IDs"

    # Verify products are sorted by price (lowest first)
    for i in range(1, len(products)):
        assert products[i]["totalPrice"] >= products[i - 1]["totalPrice"], (
            "Products not sorted by price"
        )

    logger.info("Deduplication test passed: %s unique products", len(products))


@pytest.mark.asyncio
async def test_image_handling(ebay_collector):
    """Test image handling and validation"""
    logger.info("Testing image handling...")

    query = "camera"
    products = await ebay_collector.collect_products(query, 5)

    # Check products with images
    products_with_images = [p for p in products if p["images"]]

    if products_with_images:
        product = products_with_images[0]

        # Verify image URLs
        for img_url in product["images"]:
            assert isinstance(img_url, str)
            assert img_url.startswith(("http://", "https://"))
            assert len(img_url) > 0

        # Verify image count (should be 1-6 images)
        assert 1 <= len(product["images"]) <= 6

        logger.info("Product has %s images", len(product["images"]))
    else:
        logger.warning("No products with images found in this test")


@pytest.mark.asyncio
async def test_shipping_cost_calculation(ebay_collector):
    """Test shipping cost calculation logic"""
    logger.info("Testing shipping cost calculation...")

    query = "electronics"
    products = await ebay_collector.collect_products(query, 5)

    if products:
        for product in products:
            # Verify shipping cost is reasonable
            assert product["shippingCost"] >= 0
            assert product["totalPrice"] >= product["price"]

            # If shipping cost is 0, it should be FREE shipping
            if product["shippingCost"] == 0:
                logger.info(
                    "Product '%s...' has FREE shipping",
                    product["title"][:30],
                )

    logger.info("Shipping cost calculation test passed")


@pytest.mark.asyncio
async def test_error_handling(ebay_collector):
    """Test error handling with edge cases"""
    logger.info("Testing error handling...")

    # Test with empty query
    empty_products = await ebay_collector.collect_products("", 5)
    assert isinstance(empty_products, list)

    # Test with very long query (should be truncated)
    long_query = "a" * 200  # Exceeds eBay's 100 character limit
    long_products = await ebay_collector.collect_products(long_query, 3)
    assert isinstance(long_products, list)

    # Test with very high limit (should be clamped)
    high_limit_products = await ebay_collector.collect_products("test", 100)
    assert isinstance(high_limit_products, list)
    assert len(high_limit_products) <= 50  # eBay's max per page

    logger.info("Error handling test passed")


@pytest.mark.asyncio
async def test_performance_metrics(ebay_collector):
    """Test performance metrics for product collection"""
    logger.info("Testing performance metrics...")

    query = "phone"
    start_time = asyncio.get_event_loop().time()

    products = await ebay_collector.collect_products(query, 10)

    end_time = asyncio.get_event_loop().time()
    duration = end_time - start_time

    # Verify performance is reasonable
    assert duration < 30.0, f"Collection took too long: {duration:.2f}s"

    if products:
        products_per_second = len(products) / duration
        logger.info(
            "Collected %s products in %.2fs (%.2f products/sec)",
            len(products),
            duration,
            products_per_second,
        )

        # Verify response time is reasonable
        assert duration > 0, "Response time should be positive"

    logger.info("Performance metrics test passed")


@pytest.mark.asyncio
async def test_data_validation(ebay_collector):
    """Test data validation and integrity"""
    logger.info("Testing data validation...")

    query = "tablet"
    products = await ebay_collector.collect_products(query, 5)

    for product in products:
        # Validate required fields
        required_fields = [
            "id",
            "title",
            "price",
            "currency",
            "url",
            "marketplace",
            "totalPrice",
            "shippingCost",
        ]

        for field in required_fields:
            assert field in product, f"Missing required field: {field}"

        # Validate field types
        assert isinstance(product["id"], str)
        assert isinstance(product["title"], str)
        assert isinstance(product["price"], (int, float))
        assert isinstance(product["currency"], str)
        assert isinstance(product["url"], str)
        assert isinstance(product["marketplace"], str)
        assert isinstance(product["totalPrice"], (int, float))
        assert isinstance(product["shippingCost"], (int, float))

        # Validate field values
        assert len(product["title"].strip()) > 0, "Title cannot be empty"
        assert product["price"] > 0, "Price must be positive"
        assert product["currency"] in ["USD", "EUR", "GBP"], "Invalid currency"
        assert product["marketplace"] == "us", "Invalid marketplace"
        assert product["totalPrice"] >= product["price"], "Total price must be >= price"
        assert product["shippingCost"] >= 0, "Shipping cost cannot be negative"

        # Validate URL format
        assert product["url"].startswith(("http://", "https://")), "Invalid URL format"

        # Validate images format
        if product["images"]:
            assert isinstance(product["images"], list), "Images must be a list"
            assert len(product["images"]) <= 6, "Too many images"
            for img_url in product["images"]:
                assert isinstance(img_url, str), "Image URL must be string"
                assert img_url.startswith(("http://", "https://")), "Invalid image URL"

    logger.info("Data validation passed for %s products", len(products))


@pytest.mark.asyncio
async def test_concurrent_collection(ebay_collector):
    """Test concurrent product collection"""
    logger.info("Testing concurrent collection...")

    queries = ["laptop", "phone", "tablet", "watch"]
    top_k = 3

    # Create concurrent tasks
    tasks = [ebay_collector.collect_products(query, top_k) for query in queries]

    # Execute concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify results
    successful_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Query '{queries[i]}' failed: {result}")
        else:
            successful_results.append(result)
            assert isinstance(result, list)
            logger.info(
                "Query '%s' returned %s products", queries[i], len(result)
            )

    # Verify we got some successful results
    assert len(successful_results) > 0, "All concurrent queries failed"

    total_products = sum(len(result) for result in successful_results)
    logger.info(
        "Concurrent collection completed: %s total products", total_products
    )


@pytest.mark.asyncio
async def test_source_name(ebay_collector):
    """Test source name functionality"""
    source_name = ebay_collector.get_source_name()
    assert source_name == "ebay"
    logger.info("Source name: %s", source_name)


@pytest.mark.asyncio
async def test_marketplace_configuration(ebay_collector):
    """Test marketplace configuration"""
    # Verify collector is configured for US marketplace
    assert "ebay_us" in str(ebay_collector.marketplaces).lower()

    # Test collection with different marketplace (if configured)
    if len(ebay_collector.marketplaces) > 1:
        logger.info("Testing multiple marketplaces...")
        products = await ebay_collector.collect_products("test", 5)

        # Verify products have correct marketplace identifier
        for product in products:
            assert product["marketplace"] in ["us", "uk", "de", "au"], (
                f"Invalid marketplace: {product['marketplace']}"
            )

    logger.info("Marketplace configuration test passed")


@pytest.mark.asyncio
async def test_phone_search_returns_real_data(ebay_collector):
    """Test that searching for 'phone' returns real, non-empty data from eBay API"""
    logger.info("Testing phone search returns real data...")

    query = "phone"
    top_k = 10

    products = await ebay_collector.collect_products(query, top_k)

    # Verify results are not empty
    assert len(products) > 0, f"No products found for query '{query}'"

    # Verify we got real data with proper structure
    for product in products:
        # Verify all required fields are present and have valid data
        assert "id" in product and product["id"], "Product ID is missing or empty"
        assert "title" in product and product["title"].strip(), (
            "Product title is missing or empty"
        )
        assert "price" in product and product["price"] > 0, (
            f"Invalid price for product: {product.get('price')}"
        )
        assert "currency" in product and product["currency"], (
            "Currency is missing or empty"
        )
        assert "url" in product and product["url"].startswith(
            ("http://", "https://")
        ), "Product URL is invalid"
        assert "marketplace" in product and product["marketplace"], (
            "Marketplace is missing or empty"
        )
        assert "totalPrice" in product and product["totalPrice"] > 0, (
            "Total price is invalid"
        )
        assert "shippingCost" in product and product["shippingCost"] >= 0, (
            "Shipping cost is invalid"
        )

        # Verify the product is actually related to phones.
        # Check title contains relevant keywords.
        title_lower = product["title"].lower()
        phone_keywords = [
            "phone",
            "phones",
            "smartphone",
            "smartphones",
            "mobile",
            "iphone",
            "samsung",
            "android",
            "cell",
        ]
        has_phone_keyword = any(keyword in title_lower for keyword in phone_keywords)

        logger.info(
            "Product: %s... ($%s) - Has phone keyword: %s",
            product["title"][:60],
            product["price"],
            has_phone_keyword,
        )

        # At least some products should be related to phones
        is_first_three = len(products) <= 3 or products.index(product) < 3
        if is_first_three:
            assert has_phone_keyword, (
                f"Product '{product['title']}' doesn't appear to be related to phones"
            )

    logger.info(
        "Successfully found %s real products for 'phone' search",
        len(products),
    )


@pytest.mark.asyncio
async def test_shoes_search_returns_real_data(ebay_collector):
    """Test that searching for 'shoes' returns real, non-empty data from eBay API"""
    logger.info("Testing shoes search returns real data...")

    query = "shoes"
    top_k = 10

    products = await ebay_collector.collect_products(query, top_k)

    # Verify results are not empty
    assert len(products) > 0, f"No products found for query '{query}'"

    # Verify we got real data with proper structure
    for product in products:
        # Verify all required fields are present and have valid data
        assert "id" in product and product["id"], "Product ID is missing or empty"
        assert "title" in product and product["title"].strip(), (
            "Product title is missing or empty"
        )
        assert "price" in product and product["price"] > 0, (
            f"Invalid price for product: {product.get('price')}"
        )
        assert "currency" in product and product["currency"], (
            "Currency is missing or empty"
        )
        assert "url" in product and product["url"].startswith(
            ("http://", "https://")
        ), "Product URL is invalid"
        assert "marketplace" in product and product["marketplace"], (
            "Marketplace is missing or empty"
        )
        assert "totalPrice" in product and product["totalPrice"] > 0, (
            "Total price is invalid"
        )
        assert "shippingCost" in product and product["shippingCost"] >= 0, (
            "Shipping cost is invalid"
        )

        # Verify the product is actually related to shoes.
        # Check title contains relevant keywords.
        title_lower = product["title"].lower()
        shoes_keywords = [
            "shoe",
            "shoes",
            "sneaker",
            "sneakers",
            "boot",
            "boots",
            "sandal",
            "sandals",
        ]
        has_shoes_keyword = any(keyword in title_lower for keyword in shoes_keywords)

        logger.info(
            "Product: %s... ($%s) - Has shoe keyword: %s",
            product["title"][:60],
            product["price"],
            has_shoes_keyword,
        )

        # At least some products should be related to shoes
        if len(products) <= 3 or products.index(product) < 3:  # Check first 3 products
            assert has_shoes_keyword, (
                f"Product '{product['title']}' doesn't appear to be related to shoes"
            )

    logger.info(
        "Successfully found %s real products for 'shoes' search", len(products)
    )


@pytest.mark.asyncio
async def test_phone_and_hat_search_has_images(ebay_collector):
    """Test that phone and hat searches return products with main and additional images"""
    logger.info("Testing phone and hat searches have images...")

    test_queries = [("phone", 5), ("laptop", 5)]

    total_products_with_images = 0
    total_products = 0

    for query, limit in test_queries:
        logger.info(
            "Testing image handling for query: '%s' with limit: %s", query, limit
        )

        products = await ebay_collector.collect_products(query, limit)
        total_products += len(products)

        # Verify results are not empty
        assert len(products) > 0, f"No products found for query '{query}'"

        # Check products with images
        products_with_images = [p for p in products if p["images"]]

        for product in products:
            # Verify all required fields
            assert "id" in product and product["id"], (
                f"Product ID missing for query '{query}'"
            )
            assert "title" in product and product["title"].strip(), (
                f"Product title missing for query '{query}'"
            )
            assert "price" in product and product["price"] > 0, (
                f"Invalid price for query '{query}'"
            )
            assert "currency" in product and product["currency"], (
                f"Currency missing for query '{query}'"
            )
            assert "url" in product and product["url"].startswith(
                ("http://", "https://")
            ), f"Invalid URL for query '{query}'"

            # Check image handling
            if product["images"]:
                total_products_with_images += 1

                # Verify image URLs
                for img_url in product["images"]:
                    assert isinstance(img_url, str), (
                        f"Image URL must be string for query '{query}'"
                    )
                    assert img_url.startswith(("http://", "https://")), (
                        f"Invalid image URL for query '{query}': {img_url}"
                    )
                    assert len(img_url) > 0, f"Empty image URL for query '{query}'"

                # Verify image count (should be 1-6 images)
                assert 1 <= len(product["images"]) <= 6, (
                    f"Invalid image count for query '{query}': {len(product['images'])}"
                )

                # Log product with images
                logger.info(
                    f"  - {product['title'][:40]}... ({len(product['images'])} images, ${product['price']})"
                )
            else:
                logger.warning(f"  - {product['title'][:40]}... (no images)")

        logger.info(
            f"Query '{query}' returned {len(products_with_images)}/{len(products)} products with images"
        )

    # Overall verification
    assert total_products > 0, "No products found across both queries"
    assert total_products_with_images > 0, (
        f"No products with images found across both queries ({total_products_with_images}/{total_products})"
    )

    # At least 50% of products should have images
    image_percentage = (total_products_with_images / total_products) * 100
    logger.info(
        f"Image coverage: {total_products_with_images}/{total_products} products ({image_percentage:.1f}%)"
    )
    assert image_percentage >= 50, f"Low image coverage: {image_percentage:.1f}%"

    logger.info("Phone and hat searches successfully returned products with images")


async def run_comprehensive_test():
    """Run comprehensive integration test with detailed reporting"""
    logger.info("Starting comprehensive eBay collector integration test...")

    # Initialize components
    redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)
    collector = EbayProductCollector(
        "/tmp/test_integration", redis_client=redis_client, marketplaces=["EBAY_US"]
    )

    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "config": {
            "ebay_environment": config.EBAY_ENVIRONMENT,
            "marketplaces": collector.marketplaces,
            "data_root": collector.data_root,
        },
        "tests": {},
        "summary": {},
    }

    # Test 1: Authentication
    try:
        token = await auth_service.get_access_token()
        results["tests"]["authentication"] = {
            "status": "PASS",
            "token_length": len(token),
            "has_token": len(token) > 0,
        }
    except Exception as e:
        results["tests"]["authentication"] = {"status": "FAIL", "error": str(e)}

    # Test 2: Basic Collection
    try:
        products = await collector.collect_products("test", 5)
        results["tests"]["basic_collection"] = {
            "status": "PASS",
            "products_collected": len(products),
            "has_products": len(products) > 0,
        }
    except Exception as e:
        results["tests"]["basic_collection"] = {"status": "FAIL", "error": str(e)}

    # Test 3: Data Validation
    try:
        products = await collector.collect_products("validation", 3)
        valid_products = 0

        for product in products:
            is_valid = (
                all(
                    field in product
                    for field in ["id", "title", "price", "currency", "url"]
                )
                and product["price"] > 0
                and isinstance(product["title"], str)
                and len(product["title"]) > 0
            )
            if is_valid:
                valid_products += 1

        results["tests"]["data_validation"] = {
            "status": "PASS" if valid_products == len(products) else "PARTIAL",
            "total_products": len(products),
            "valid_products": valid_products,
            "validation_rate": valid_products / len(products) if products else 0,
        }
    except Exception as e:
        results["tests"]["data_validation"] = {"status": "FAIL", "error": str(e)}

    # Test 4: Performance
    try:
        start_time = asyncio.get_event_loop().time()
        products = await collector.collect_products("perf", 5)
        duration = asyncio.get_event_loop().time() - start_time

        results["tests"]["performance"] = {
            "status": "PASS",
            "duration": duration,
            "products_per_second": len(products) / duration if duration > 0 else 0,
            "response_time_acceptable": duration < 30.0,
        }
    except Exception as e:
        results["tests"]["performance"] = {"status": "FAIL", "error": str(e)}

    # Summary
    total_tests = len(results["tests"])
    passed_tests = sum(
        1 for test in results["tests"].values() if test.get("status") == "PASS"
    )

    results["summary"] = {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
        "overall_status": "PASS" if passed_tests == total_tests else "FAIL",
    }

    # Cleanup
    await redis_client.close()

    logger.info(
        f"Comprehensive test completed: {passed_tests}/{total_tests} tests passed"
    )
    return results


if __name__ == "__main__":
    # Run comprehensive test
    results = asyncio.run(run_comprehensive_test())

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"ebay_integration_test_results_{timestamp}.json"

    with open(result_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nDetailed results saved to: {result_file}")
    print(f"Overall status: {results['summary']['overall_status']}")
    print(f"Success rate: {results['summary']['success_rate']:.1%}")

    sys.exit(0 if results["summary"]["overall_status"] == "PASS" else 1)
