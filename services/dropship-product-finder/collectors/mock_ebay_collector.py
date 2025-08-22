from typing import List, Dict, Any, Optional
from common_py.logging_config import configure_logging
from .base_product_collector import BaseProductCollector

logger = configure_logging("dropship-product-finder")


class MockEbayCollector(BaseProductCollector):
    """Mock eBay collector that returns fixed phone products without external dependencies"""
    
    def __init__(self, data_root: str, marketplaces: Optional[List[str]] = None,
                 httpx_client: Optional[Any] = None, redis_client: Optional[Any] = None):
        super().__init__(data_root)
        # Use default marketplace
        self.marketplaces = marketplaces or ["EBAY_US"]
        self.base_url = "https://api.sandbox.ebay.com/buy/browse/v1"
        self.browse_clients = {}
        logger.info(f"Initialized MockEbayCollector for marketplaces: {self.marketplaces}")
    
    async def collect_products(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Collect products for eBay marketplace with fixed 'phone' query"""
        logger.info(f"Collecting eBay products - query=phone (fixed) - top_k={top_k} - marketplaces={self.marketplaces}")
        
        # Return mock phone products without calling real eBay API
        mock_products = [
            {
                "id": "mock-phone-001",
                "product_id": "mock-phone-001",
                "itemId": "mock-phone-001",
                "title": "Samsung Galaxy S21 - 128GB - Unlocked",
                "brand": "Samsung",
                "url": "https://mock.ebay.com/itm/samsung-galaxy-s21",
                "image_url": "https://via.placeholder.com/300x300?text=Samsung+Galaxy+S21",
                "images": ["https://via.placeholder.com/300x300?text=Samsung+Galaxy+S21"],
                "marketplace": "us",
                "price": 699.99,
                "currency": "USD",
                "epid": None,
                "totalPrice": 699.99,
                "shippingCost": 0,
                "source": "ebay"
            },
            {
                "id": "mock-phone-002",
                "product_id": "mock-phone-002",
                "itemId": "mock-phone-002",
                "title": "iPhone 13 Pro - 256GB - Unlocked - Space Gray",
                "brand": "Apple",
                "url": "https://mock.ebay.com/itm/iphone-13-pro",
                "image_url": "https://via.placeholder.com/300x300?text=iPhone+13+Pro",
                "images": ["https://via.placeholder.com/300x300?text=iPhone+13+Pro"],
                "marketplace": "us",
                "price": 999.99,
                "currency": "USD",
                "epid": None,
                "totalPrice": 999.99,
                "shippingCost": 0,
                "source": "ebay"
            }
        ]
        
        return mock_products[:top_k]
    
    def get_source_name(self) -> str:
        """Return the source name"""
        return "ebay"