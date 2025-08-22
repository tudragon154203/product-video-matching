from typing import List, Dict, Any
from common_py.logging_config import configure_logging
from .base_product_collector import BaseProductCollector

logger = configure_logging("dropship-product-finder")


class MockProductCollector(BaseProductCollector):
    """Mock product collector for testing"""
    
    async def collect_products(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Collect mock products"""
        source = self.get_source_name()
        logger.info(f"Collecting {source} products", query=query, count=top_k)
        
        # Mock product data for MVP
        mock_products = []
        for i in range(min(top_k, 5)):  # Limit to 5 for testing
            product = {
                "id": f"{source}_{query}_{i}",
                "title": f"Mock {query} Product {i+1}",
                "brand": f"{source.capitalize()}{i+1}",
                "url": f"https://{source}.com/mock-product-{i}",
                "images": [
                    f"https://picsum.photos/400/400?random={i*10+j}"
                    for j in range(1 + (i % 3))  # 1-4 representative images
                ],
                "marketplace": "us"  # Add marketplace field with 'us' value
            }
            mock_products.append(product)
        
        logger.info(f"Collected {source} products", count=len(mock_products))
        return mock_products
    
    def get_source_name(self) -> str:
        """Return the source name"""
        # Return "mock" by default, but subclasses can override this
        return "mock"