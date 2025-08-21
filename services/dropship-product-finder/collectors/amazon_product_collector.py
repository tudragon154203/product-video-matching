from .mock_product_collector import MockProductCollector
from typing import List, Dict, Any

class AmazonProductCollector(MockProductCollector):
    """Amazon product collector (currently mock implementation)"""
    
    async def collect_products(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Collect products for a keyword query; return normalized dicts."""
        pass