from typing import List, Dict, Any
from common_py.logging_config import configure_logging
from .ebay_product_collector import EbayProductCollector

logger = configure_logging("dropship-product-finder")


class MockEbayCollector(EbayProductCollector):
    """Mock eBay collector that inherits from real EbayProductCollector but uses fixed 'phone' query"""
    
    async def collect_products(self, top_k: int) -> List[Dict[str, Any]]:
        """Collect products for eBay marketplace with fixed 'phone' query"""
        logger.info(f"Collecting eBay products with fixed 'phone' query", top_k=top_k, marketplaces=self.marketplaces)
        
        # Use the parent's collect_products method but with fixed "phone" query
        return await super().collect_products("phone", top_k)
    
    def get_source_name(self) -> str:
        """Return the source name"""
        return "ebay"