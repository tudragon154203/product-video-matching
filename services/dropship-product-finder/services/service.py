import uuid
from typing import Dict, Any, List, Optional
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.logging_config import configure_logging
from collectors.base_product_collector import BaseProductCollector
from collectors.amazon_product_collector import AmazonProductCollector
from collectors.ebay_product_collector import EbayProductCollector
from config_loader import config
from .product_collection_manager import ProductCollectionManager
from .image_storage_manager import ImageStorageManager
from collectors.mock_ebay_collector import MockEbayCollector

logger = configure_logging("dropship-product-finder")


class DropshipProductFinderService:
    """Main service class for product collection"""
    
    def __init__(self, db: DatabaseManager, broker: MessageBroker, data_root: str, redis_client: Optional = None):        
        self.db = db
        self.broker = broker
        self.redis = redis_client
        
        # Initialize collectors based on configuration
        if config.USE_MOCK_FINDERS:
            logger.info("Using mock product finders for development")
            
            self.collectors: Dict[str, BaseProductCollector] = {
                "amazon": AmazonProductCollector(data_root), 
                "ebay": MockEbayCollector(data_root)
            }
        else:
            logger.info("Using real product finders (Amazon and eBay APIs)")
            self.collectors: Dict[str, BaseProductCollector] = {
                "amazon": AmazonProductCollector(data_root),
                "ebay": EbayProductCollector(
                    data_root=data_root,
                    redis_client=self.redis
                )
            }
        
        self.image_storage_manager = ImageStorageManager(db, broker, self.collectors)
        self.product_collection_manager = ProductCollectionManager(self.collectors, self.image_storage_manager)

    async def handle_products_collect_request(self, event_data: Dict[str, Any]):
        """Handle products collection request"""
        try:
            job_id = event_data["job_id"]
            queries = event_data["queries"]["en"]  # Use English queries
            top_amz = event_data["top_amz"]
            top_ebay = event_data["top_ebay"]
            
            logger.info("Processing product collection request",
                       job_id=job_id, query_count=len(queries))
            
            amazon_count, ebay_count = await self.product_collection_manager.collect_and_store_products(job_id, queries, top_amz, top_ebay)
            
            total_images = await self.db.fetch_val(
                """
                SELECT COUNT(*) 
                FROM product_images pi 
                JOIN products p ON pi.product_id = p.product_id 
                WHERE p.job_id = $1
                """,
                job_id
            ) or 0
            
            logger.info("Collected all products and images",
                       job_id=job_id,
                       amazon_count=amazon_count,
                       ebay_count=ebay_count,
                       total_images=total_images)
            
            if total_images == 0:
                await self._handle_zero_products_case(job_id)
            else:
                await self._publish_all_image_events(job_id, total_images)
                
                logger.info("Completed product collection",
                           job_id=job_id,
                           amazon_count=amazon_count,
                           ebay_count=ebay_count,
                           total_images=total_images)
            
        except Exception as e:
            logger.error("Failed to process product collection request", error=str(e))
            raise
    
    async def _handle_zero_products_case(self, job_id: str):
        logger.info("No products found for job {job_id}", job_id=job_id)
        
        event_id = str(uuid.uuid4())
        await self.broker.publish_event(
            "products.collections.completed",
            {
                "job_id": job_id,
                "event_id": event_id
            },
            correlation_id=job_id
        )
        
        vision_event_id = str(uuid.uuid4())
        await self.broker.publish_event(
            "products.images.ready.batch",
            {
                "job_id": job_id,
                "event_id": vision_event_id,
                "total_images": 0
            },
            correlation_id=job_id
        )
        
        logger.info("Published products.images.ready.batch with zero images",
                   job_id=job_id,
                   event_id=vision_event_id,
                   total_images=0)
        
        logger.info("Skipping individual image events for job with no products", job_id=job_id)

    async def _publish_all_image_events(self, job_id: str, total_images: int):
        event_id = str(uuid.uuid4())
        await self.broker.publish_event(
            "products.collections.completed",
            {
                "job_id": job_id,
                "event_id": event_id
            },
            correlation_id=job_id
        )
        
        vision_event_id = str(uuid.uuid4())
        await self.broker.publish_event(
            "products.images.ready.batch",
            {
                "job_id": job_id,
                "event_id": vision_event_id,
                "total_images": total_images
            },
            correlation_id=job_id
        )
        
        logger.info("Published products.images.ready.batch",
                   job_id=job_id,
                   event_id=vision_event_id,
                   total_images=total_images)
        
        await self.image_storage_manager.publish_individual_image_events(job_id)
    
    async def close(self):
        """Close all collectors"""
        for collector in self.collectors.values():
            await collector.close()
