from typing import Dict, Any, List
from common_py.logging_config import configure_logging
from collectors.interface import IProductCollector
from .image_storage_manager import ImageStorageManager

logger = configure_logging("dropship-product-finder")

class ProductCollectionManager:
    def __init__(self, collectors: Dict[str, IProductCollector], image_storage_manager: ImageStorageManager):
        self.collectors = collectors
        self.image_storage_manager = image_storage_manager

    async def collect_and_store_products(self, job_id: str, queries: List[str], top_amz: int, top_ebay: int) -> tuple[int, int]:
        amazon_count = 0
        ebay_count = 0
        
        for query in queries:
            ebay_products = await self.collectors["ebay"].collect_products(query, top_ebay)
            for product_data in ebay_products:
                await self.image_storage_manager.store_product(product_data, job_id, "ebay")
                ebay_count += 1

        for query in queries:
            amazon_products = await self.collectors["amazon"].collect_products(query, top_amz)
            for product_data in amazon_products:
                await self.image_storage_manager.store_product(product_data, job_id, "amazon")
                amazon_count += 1
        
        return amazon_count, ebay_count
