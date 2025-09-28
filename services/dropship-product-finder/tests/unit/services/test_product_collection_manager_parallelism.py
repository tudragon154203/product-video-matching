import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from services.product_collection_manager import ProductCollectionManager
from collectors.interface import IProductCollector


class MockProductCollector(IProductCollector):
    def __init__(self, products_to_return: List[Dict[str, Any]], should_fail: bool = False):
        self.products_to_return = products_to_return
        self.should_fail = should_fail
        self.call_count = 0

    async def collect_products(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        self.call_count += 1
        if self.should_fail:
            raise Exception("Collector failed")
        return self.products_to_return[:top_k]


class MockImageStorageManager:
    def __init__(self, should_fail: bool = False, fail_on_product_id: str = None):
        self.stored_products = []
        self.should_fail = should_fail
        self.fail_on_product_id = fail_on_product_id

    async def store_product(self, product: Dict[str, Any], job_id: str, platform: str) -> None:
        if self.should_fail and (self.fail_on_product_id is None or product.get('id') == self.fail_on_product_id):
            raise Exception(f"Storage failed for product {product.get('id')}")
        self.stored_products.append({
            'product': product,
            'job_id': job_id,
            'platform': platform
        })


@pytest.fixture
def mock_collectors():
    return {
        "amazon": MockProductCollector([
            {"id": "amz_1", "title": "Amazon Product 1"},
            {"id": "amz_2", "title": "Amazon Product 2"}
        ]),
        "ebay": MockProductCollector([
            {"id": "ebay_1", "title": "eBay Product 1"},
            {"id": "ebay_2", "title": "eBay Product 2"},
            {"id": "ebay_3", "title": "eBay Product 3"}
        ])
    }


@pytest.fixture
def mock_storage_manager():
    return MockImageStorageManager()


@pytest.fixture
def product_collection_manager(mock_collectors, mock_storage_manager):
    return ProductCollectionManager(mock_collectors, mock_storage_manager)


@pytest.mark.asyncio
async def test_parallel_execution_basic(product_collection_manager):
    """Test that Amazon and eBay workers run in parallel and return correct counts."""
    queries = ["query1", "query2"]
    top_amz = 2
    top_ebay = 3
    
    amazon_count, ebay_count = await product_collection_manager.collect_and_store_products(
        "test_job", queries, top_amz, top_ebay
    )
    
    # Verify counts
    assert amazon_count == 4  # 2 queries * 2 products each
    assert ebay_count == 6    # 2 queries * 3 products each
    
    # Verify all products were stored
    assert len(product_collection_manager.image_storage_manager.stored_products) == 10


@pytest.mark.asyncio
async def test_collector_failure_handling(product_collection_manager):
    """Test that collector failures are handled gracefully without crashing the entire process."""
    # Make eBay collector fail
    product_collection_manager.collectors["ebay"].should_fail = True
    
    queries = ["query1", "query2"]
    top_amz = 2
    top_ebay = 3
    
    amazon_count, ebay_count = await product_collection_manager.collect_and_store_products(
        "test_job", queries, top_amz, top_ebay
    )
    
    # Amazon should still work, eBay should return 0 due to failures
    assert amazon_count == 4
    assert ebay_count == 0
    
    # Only Amazon products should be stored
    amazon_stored = [p for p in product_collection_manager.image_storage_manager.stored_products 
                    if p['platform'] == 'amazon']
    assert len(amazon_stored) == 4


@pytest.mark.asyncio
async def test_storage_failure_handling(product_collection_manager):
    """Test that storage failures are handled gracefully without crashing the entire process."""
    # Make storage manager fail on specific product
    product_collection_manager.image_storage_manager.should_fail = True
    product_collection_manager.image_storage_manager.fail_on_product_id = "amz_1"
    
    queries = ["query1"]
    top_amz = 2
    top_ebay = 2
    
    amazon_count, ebay_count = await product_collection_manager.collect_and_store_products(
        "test_job", queries, top_amz, top_ebay
    )
    
    # Amazon count should be 1 (only amz_2 succeeded), eBay count should be 2
    assert amazon_count == 1
    assert ebay_count == 2
    
    # Verify only non-failed products were stored
    stored_products = product_collection_manager.image_storage_manager.stored_products
    assert len(stored_products) == 3  # amz_2 + ebay_1 + ebay_2


@pytest.mark.asyncio
async def test_empty_queries(product_collection_manager):
    """Test behavior with empty queries list."""
    queries = []
    top_amz = 2
    top_ebay = 3
    
    amazon_count, ebay_count = await product_collection_manager.collect_and_store_products(
        "test_job", queries, top_amz, top_ebay
    )
    
    # Both counts should be 0
    assert amazon_count == 0
    assert ebay_count == 0
    assert len(product_collection_manager.image_storage_manager.stored_products) == 0


@pytest.mark.asyncio
async def test_zero_top_k(product_collection_manager):
    """Test behavior with top_k = 0."""
    queries = ["query1"]
    top_amz = 0
    top_ebay = 0
    
    amazon_count, ebay_count = await product_collection_manager.collect_and_store_products(
        "test_job", queries, top_amz, top_ebay
    )
    
    # Both counts should be 0
    assert amazon_count == 0
    assert ebay_count == 0
    assert len(product_collection_manager.image_storage_manager.stored_products) == 0


@pytest.mark.asyncio
async def test_concurrency_verification():
    """Test that workers actually run in parallel by using timing."""
    # Create a mock collector that simulates work
    async def slow_collect_products(query: str, top_k: int) -> List[Dict[str, Any]]:
        await asyncio.sleep(0.1)  # Simulate network delay
        return [{"id": f"prod_{query}_{i}", "title": f"Product {i}"} for i in range(top_k)]
    
    # Create mock collectors with slow operations
    slow_amazon_collector = AsyncMock()
    slow_amazon_collector.collect_products.side_effect = slow_collect_products
    
    slow_ebay_collector = AsyncMock()
    slow_ebay_collector.collect_products.side_effect = slow_collect_products
    
    mock_collectors = {
        "amazon": slow_amazon_collector,
        "ebay": slow_ebay_collector
    }
    
    mock_storage_manager = MockImageStorageManager()
    manager = ProductCollectionManager(mock_collectors, mock_storage_manager)
    
    queries = ["query1"]
    top_amz = 2
    top_ebay = 2
    
    import time
    start_time = time.time()
    
    await manager.collect_and_store_products("test_job", queries, top_amz, top_ebay)
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # Since workers run in parallel, total time should be roughly the time of one worker,
    # not the sum of both workers
    # Each worker takes ~0.1s for collect + small time for storage
    # So total should be < 0.3s (sequential would be ~0.4s)
    assert elapsed < 0.3, f"Expected parallel execution, but took {elapsed:.3f}s"
    
    # Verify both collectors were called
    assert slow_amazon_collector.collect_products.call_count == 1
    assert slow_ebay_collector.collect_products.call_count == 1


@pytest.mark.asyncio
async def test_product_id_logging_in_storage_error():
    """Test that product ID is properly logged in storage errors."""
    with patch('services.product_collection_manager.logger') as mock_logger:
        # Make storage fail on a specific product
        mock_storage_manager = MockImageStorageManager(should_fail=True, fail_on_product_id="test_prod_123")
        manager = ProductCollectionManager({
            "amazon": MockProductCollector([{"id": "test_prod_123", "title": "Test Product"}]),
            "ebay": MockProductCollector([])
        }, mock_storage_manager)
        
        await manager.collect_and_store_products("test_job", ["query1"], 1, 0)
        
        # Verify that the exception was logged with the product ID
        mock_logger.exception.assert_called()
        # Check that one of the exception calls contains the expected message
        exception_calls = [call for call in mock_logger.exception.call_args_list]
        assert any("id=test_prod_123" in str(call) for call in exception_calls)


@pytest.mark.asyncio
async def test_collector_logging_on_failure():
    """Test that collector failures are properly logged."""
    with patch('services.product_collection_manager.logger') as mock_logger:
        failing_collector = MockProductCollector([], should_fail=True)
        manager = ProductCollectionManager({
            "amazon": failing_collector,
            "ebay": MockProductCollector([])
        }, MockImageStorageManager())
        
        await manager.collect_and_store_products("test_job", ["query1"], 1, 0)
        
        # Verify that the collector failure was logged
        mock_logger.exception.assert_called()
        # Check that the exception contains the expected query
        exception_calls = [call for call in mock_logger.exception.call_args_list]
        assert any("query='query1'" in str(call) for call in exception_calls)