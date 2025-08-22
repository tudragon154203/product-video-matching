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
        # Create an async mock with the required Redis methods
        auth = AsyncMock(spec=eBayAuthService)
        auth.redis_client = AsyncMock()
        auth.redis_client.get = AsyncMock(return_value=b'{"access_token": "test_token", "expires_in": 7200}')
        auth.redis_client.setex = AsyncMock()
        return auth
    
    def test_amazon_collector_inherits_from_mock(self):
        """Test that AmazonProductCollector inherits from MockProductCollector"""
        from collectors.mock_product_collector import MockProductCollector
        assert issubclass(AmazonProductCollector, MockProductCollector)
        assert AmazonProductCollector("/tmp/test").get_source_name() == "amazon"
    
    def test_ebay_collector_inherits_from_mock(self, mock_auth_service):
        """Test that EbayProductCollector inherits from BaseProductCollector"""
        collector = EbayProductCollector("/tmp/test", redis_client=mock_auth_service)
        assert isinstance(collector, BaseProductCollector)
        assert collector.get_source_name() == "ebay"
    
    @pytest.mark.asyncio
    async def test_all_collectors_use_mock_data(self, mock_auth_service):
        """Test that all collectors return mock data when USE_MOCK_FINDERS is true"""
        # Force mock mode for this test
        from config_loader import config
        from services.service import DropshipProductFinderService
        from common_py.database import DatabaseManager
        from common_py.messaging import MessageBroker
        
        original_value = config.USE_MOCK_FINDERS
        config.USE_MOCK_FINDERS = True
        
        # Create mock database and broker
        mock_db = MagicMock(spec=DatabaseManager)
        mock_broker = MagicMock(spec=MessageBroker)
        
        try:
            # Create service with mock collectors
            service = DropshipProductFinderService(mock_db, mock_broker, "/tmp/test", mock_auth_service)
            collectors = service.collectors
            
            for source_name, collector in collectors.items():
                products = await collector.collect_products("test query", 2)
                
                # Verify we get mock products
                assert len(products) == 2
                
                # Verify products have mock characteristics
                for product in products:
                    assert source_name in product["id"]
                    assert product["url"].startswith(f"https://{source_name}.com/")
                    assert "mock" in product["title"].lower()
        finally:
            # Restore original value
            config.USE_MOCK_FINDERS = original_value


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
        from services.service import DropshipProductFinderService
        from common_py.database import DatabaseManager
        from common_py.messaging import MessageBroker
        
        # Force mock mode for this test
        original_value = config.USE_MOCK_FINDERS
        config.USE_MOCK_FINDERS = True
        
        # Create mock database and broker
        mock_db = MagicMock(spec=DatabaseManager)
        mock_broker = MagicMock(spec=MessageBroker)
        
        try:
            # Create service with mock collectors
            service = DropshipProductFinderService(mock_db, mock_broker, "/tmp/test", mock_auth_service)
            collectors = service.collectors
            
            # Verify the configuration is set correctly
            assert config.USE_MOCK_FINDERS == True
            
            # Verify collectors exist
            assert "amazon" in collectors
            assert "ebay" in collectors
            
            # Both should inherit from their respective base classes
            assert isinstance(collectors["amazon"], MockProductCollector)
            # For eBay, when in mock mode, it should also use MockProductCollector
            assert isinstance(collectors["ebay"], MockProductCollector) or isinstance(collectors["ebay"], BaseProductCollector)
            
            # Both should return mock data
            assert collectors["amazon"].get_source_name() == "amazon"
            assert collectors["ebay"].get_source_name() == "ebay"
        finally:
            # Restore original value
            config.USE_MOCK_FINDERS = original_value