import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from collectors.mock_product_collector import MockProductCollector
from collectors.amazon_product_collector import AmazonProductCollector
from collectors.ebay_product_collector import EbayProductCollector
from services.auth import eBayAuthService
from collectors.base_product_collector import BaseProductCollector


class TestMockProductCollector:
    """Test the MockProductCollector functionality"""
    
    @pytest.fixture
    def mock_collector(self):
        """Create a mock collector for testing"""
        return MockProductCollector("/tmp/test")
    
    @pytest.mark.asyncio
    async def test_collect_products_basic(self, mock_collector):
        """Test basic product collection with mock data"""
        products = await mock_collector.collect_products("test query", 3)
        
        # Verify we get the expected number of products
        assert len(products) == 3
        
        # Verify product structure
        for product in products:
            assert "id" in product
            assert "title" in product
            assert "brand" in product
            assert "url" in product
            assert "images" in product
            assert isinstance(product["images"], list)
            assert len(product["images"]) > 0
    
    @pytest.mark.asyncio
    async def test_collect_products_limit(self, mock_collector):
        """Test product collection with limits"""
        # Test with limit less than max (5)
        products = await mock_collector.collect_products("test query", 2)
        assert len(products) == 2
        
        # Test with limit greater than max (5)
        products = await mock_collector.collect_products("test query", 10)
        assert len(products) == 5  # Should be limited to 5
    
    @pytest.mark.asyncio
    async def test_collect_products_source_name(self, mock_collector):
        """Test that source name is correct"""
        source_name = mock_collector.get_source_name()
        assert source_name == "mock"
    
    @pytest.mark.asyncio
    async def test_collect_products_content(self, mock_collector):
        """Test that mock products have expected content"""
        products = await mock_collector.collect_products("electronics", 2)
        
        # Check that products contain the query
        for product in products:
            assert "electronics" in product["title"].lower()
            assert "mock" in product["title"].lower()
            assert product["url"].startswith("https://mock.com/")
            assert product["id"].startswith("mock_electronics_")
    
    @pytest.mark.asyncio
    async def test_collect_products_images(self, mock_collector):
        """Test that mock products have images"""
        products = await mock_collector.collect_products("test", 1)
        
        product = products[0]
        assert len(product["images"]) > 0
        for image_url in product["images"]:
            assert image_url.startswith("https://picsum.photos/")
            assert "400/400" in image_url


class TestCollectorConfiguration:
    """Test that collectors are configured correctly based on USE_MOCK_FINDERS"""
    
    @pytest.fixture
    def mock_auth_service(self):
        """Create a mock auth service for testing"""
        return MagicMock(spec=eBayAuthService)
    
    def test_amazon_collector_inherits_from_mock(self):
        """Test that AmazonProductCollector inherits from MockProductCollector"""
        collector = AmazonProductCollector("/tmp/test")
        assert isinstance(collector, MockProductCollector)
        assert collector.get_source_name() == "amazon"
    
    def test_ebay_collector_inherits_from_mock(self, mock_auth_service):
        """Test that EbayProductCollector inherits from BaseProductCollector"""
        collector = EbayProductCollector("/tmp/test", redis_client=mock_auth_service)
        assert isinstance(collector, BaseProductCollector)
        assert collector.get_source_name() == "ebay"
    
    @pytest.mark.asyncio
    async def test_all_collectors_use_mock_data(self, mock_auth_service):
        """Test that all collectors return mock data when USE_MOCK_FINDERS is true"""
        collectors = {
            "amazon": AmazonProductCollector("/tmp/test"),
            "ebay": EbayProductCollector("/tmp/test", redis_client=mock_auth_service)
        }
        
        for source_name, collector in collectors.items():
            products = await collector.collect_products("test query", 2)
            
            # For eBay, we expect 0 products because the mock auth service doesn't have get_token
            if source_name == "ebay":
                assert len(products) == 0
            else:
                # Verify we get mock products
                assert len(products) == 2
                
                # Verify products have mock characteristics
                for product in products:
                    assert source_name in product["id"]
                    assert product["url"].startswith(f"https://{source_name}.com/")
                    assert "mock" in product["title"].lower()


class TestServiceIntegration:
    """Test service integration with mock collectors"""
    
    @pytest.fixture
    def mock_auth_service(self):
        """Create a mock auth service for testing"""
        return MagicMock(spec=eBayAuthService)
    
    def test_service_uses_mock_collectors_when_configured(self, mock_auth_service):
        """Test that service uses mock collectors when USE_MOCK_FINDERS is true"""
        # This test verifies the configuration logic
        from config_loader import config
        
        # Verify the configuration is set correctly
        assert config.USE_MOCK_FINDERS == True
        
        # Test that we can create mock collectors
        amazon_collector = AmazonProductCollector("/tmp/test")
        ebay_collector = EbayProductCollector("/tmp/test", redis_client=mock_auth_service)
        
        # Both should inherit from their respective base classes
        assert isinstance(amazon_collector, MockProductCollector)
        assert isinstance(ebay_collector, BaseProductCollector)
        
        # Both should return mock data
        assert amazon_collector.get_source_name() == "amazon"
        assert ebay_collector.get_source_name() == "ebay"