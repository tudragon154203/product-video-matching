from typing import List, Dict, Any
from .mock_product_collector import MockProductCollector

class MockEbayCollector(MockProductCollector):
    """Mock eBay collector for testing"""
    
    def get_source_name(self) -> str:
        """Return the source name"""
        return "ebay"