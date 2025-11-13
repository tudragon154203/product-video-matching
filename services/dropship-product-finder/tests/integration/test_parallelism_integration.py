import pytest
import asyncio
from services.product_collection_manager import ProductCollectionManager
pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_parallel_execution_with_real_components():
    """Integration test to verify parallel execution with mocked but realistic components."""

    # Create realistic mock collectors that simulate actual API calls
    class RealisticMockCollector:
        def __init__(self, platform: str, delay: float = 0.05):
            self.platform = platform
            self.delay = delay
            self.call_count = 0

        async def collect_products(self, query: str, top_k: int):
            self.call_count += 1
            # Simulate network delay
            await asyncio.sleep(self.delay)

            # Return realistic product data
            products = []
            for i in range(min(top_k, 3)):  # Limit to 3 products per query for testing
                products.append(
                    {
                        "id": f"{self.platform}_{query}_{i}",
                        "title": f"{self.platform.title()} Product {i} for {query}",
                        "url": f"https://example.com/{self.platform}/product/{i}",
                        "images": [
                            f"https://example.com/images/{self.platform}_{i}_1.jpg"
                        ],
                        "price": f"${10 + i * 5}",
                        "currency": "USD",
                    }
                )
            return products

    # Create realistic mock storage manager
    class RealisticMockStorageManager:
        def __init__(self):
            self.stored_products = []
            self.storage_delay = 0.01  # Simulate storage I/O delay

        async def store_product(self, product: dict, job_id: str, platform: str, correlation_id: str):
            await asyncio.sleep(self.storage_delay)  # Simulate storage operation
            self.stored_products.append(
                {"product": product, "job_id": job_id, "platform": platform}
            )

    # Create components
    amazon_collector = RealisticMockCollector("amazon", delay=0.05)
    ebay_collector = RealisticMockCollector("ebay", delay=0.05)
    storage_manager = RealisticMockStorageManager()

    collectors = {"amazon": amazon_collector, "ebay": ebay_collector}

    manager = ProductCollectionManager(collectors, storage_manager)

    # Test with multiple queries
    queries = ["electronics", "fashion", "home"]
    top_amz = 2
    top_ebay = 2

    import time

    start_time = time.time()

    amazon_count, ebay_count = await manager.collect_and_store_products(
        "integration_test_job", queries, top_amz, top_ebay, "test_correlation_id"
    )

    end_time = time.time()
    elapsed = end_time - start_time

    # Verify results
    assert amazon_count == 6  # 3 queries * 2 products each
    assert ebay_count == 6  # 3 queries * 2 products each
    assert len(storage_manager.stored_products) == 12  # Total products stored

    # Verify parallel execution (should be much faster than sequential)
    # Sequential would take: (0.05 + 0.01) * 3 * 2 * 2 = 0.72s
    # Parallel should take: (0.05 + 0.01) * 3 + 0.01 * 12 = 0.18 + 0.12 = 0.30s
    # So we expect it to be significantly less than 0.6s
    assert elapsed < 0.6, (
        f"Expected parallel execution to be faster, but took {elapsed:.3f}s"
    )

    # Verify both collectors were called for each query
    assert amazon_collector.call_count == 3
    assert ebay_collector.call_count == 3

    # Verify stored products have correct structure
    for stored in storage_manager.stored_products:
        assert "product" in stored
        assert "job_id" in stored
        assert "platform" in stored
        assert stored["job_id"] == "integration_test_job"
        assert stored["platform"] in ["amazon", "ebay"]
        assert "id" in stored["product"]
        assert "title" in stored["product"]
        assert "url" in stored["product"]
        assert "images" in stored["product"]
        assert "price" in stored["product"]
        assert "currency" in stored["product"]


@pytest.mark.asyncio
async def test_error_resilience_integration():
    """Integration test to verify error handling works end-to-end."""

    # Create a collector that fails on specific query
    class FailingCollector:
        def __init__(self, fail_on_query: str):
            self.fail_on_query = fail_on_query
            self.call_count = 0

        async def collect_products(self, query: str, top_k: int):
            self.call_count += 1
            if query == self.fail_on_query:
                raise Exception(f"Simulated failure for query: {query}")

            # Return some products for successful queries
            return [
                {
                    "id": f"prod_{query}_1",
                    "title": f"Product for {query}",
                    "url": "https://example.com/product",
                    "images": ["https://example.com/image.jpg"],
                    "price": "$20",
                    "currency": "USD",
                }
            ]

    # Create storage manager that never fails
    class ReliableStorageManager:
        def __init__(self):
            self.stored_products = []

        async def store_product(self, product: dict, job_id: str, platform: str, correlation_id: str):
            self.stored_products.append(
                {"product": product, "job_id": job_id, "platform": platform}
            )

    # Setup components
    amazon_collector = FailingCollector(
        "electronics"
    )  # Amazon will fail on "electronics"
    ebay_collector = FailingCollector("fashion")  # eBay will fail on "fashion"
    storage_manager = ReliableStorageManager()

    collectors = {"amazon": amazon_collector, "ebay": ebay_collector}

    manager = ProductCollectionManager(collectors, storage_manager)

    # Test with queries that will cause some failures
    queries = ["electronics", "fashion", "home"]
    top_amz = 1
    top_ebay = 1

    amazon_count, ebay_count = await manager.collect_and_store_products(
        "error_test_job", queries, top_amz, top_ebay, "test_correlation_id"
    )

    # Amazon should have 2 successful products (electronics failed, fashion succeeded, home succeeded)
    # eBay should have 2 successful products (electronics succeeded, fashion failed, home succeeded)
    assert amazon_count == 2
    assert ebay_count == 2
    assert len(storage_manager.stored_products) == 4

    # Verify collectors were called for all queries despite failures
    assert amazon_collector.call_count == 3
    assert ebay_collector.call_count == 3
