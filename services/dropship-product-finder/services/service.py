import uuid
import structlog
from typing import Dict, Any, List, Optional
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import ProductCRUD, ProductImageCRUD
from common_py.models import Product, ProductImage
from collectors.collectors import BaseProductCollector, MockProductCollector, AmazonProductCollector, EbayProductCollector
from .auth import eBayAuthService
from config_loader import config

logger = structlog.get_logger()


class DropshipProductFinderService:
    """Main service class for product collection"""
    
    def __init__(self, db: DatabaseManager, broker: MessageBroker, data_root: str, redis_client: Optional = None):
        self.db = db
        self.broker = broker
        self.redis = redis_client
        self.product_crud = ProductCRUD(db)
        self.image_crud = ProductImageCRUD(db)
        
        # Initialize eBay auth service if Redis is available
        self.ebay_auth = None
        if self.redis:
            from config_loader import config
            self.ebay_auth = eBayAuthService(config, self.redis)
        
        # Initialize collectors based on configuration
        if config.USE_MOCK_FINDERS:
            logger.info("Using mock product finders for development")
            self.collectors: Dict[str, BaseProductCollector] = {
                "amazon": MockProductCollector(data_root),
                "ebay": MockProductCollector(data_root)
            }
            # Disable eBay authentication service when using mock
            if self.ebay_auth:
                self.ebay_auth = None
        else:
            logger.info("Using real product finders (Amazon and eBay APIs)")
            self.collectors: Dict[str, BaseProductCollector] = {
                "amazon": AmazonProductCollector(data_root),
                "ebay": EbayProductCollector(data_root, self.ebay_auth)
            }
    
    async def handle_products_collect_request(self, event_data: Dict[str, Any]):
        """Handle products collection request"""
        try:
            job_id = event_data["job_id"]
            queries = event_data["queries"]["en"]  # Use English queries
            top_amz = event_data["top_amz"]
            top_ebay = event_data["top_ebay"]
            
            logger.info("Processing product collection request",
                       job_id=job_id, query_count=len(queries))
            
            # Collect and store all products first (without publishing individual image events)
            amazon_count = 0
            ebay_count = 0
            
            # Collect Amazon products for each query
            for query in queries:
                amazon_products = await self.collectors["amazon"].collect_products(query, top_amz)
                for product_data in amazon_products:
                    await self.store_product(product_data, job_id, "amazon")
                    amazon_count += 1
            
            # Collect eBay products for each query
            for query in queries:
                ebay_products = await self.collectors["ebay"].collect_products(query, top_ebay)
                for product_data in ebay_products:
                    await self.store_product(product_data, job_id, "ebay")
                    ebay_count += 1
            
            # Count total images for this job
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
            
            # Handle zero products case
            if total_images == 0:
                logger.info("No products found for job {job_id}", job_id=job_id)
                
                # Emit products collections completed event
                event_id = str(uuid.uuid4())
                await self.broker.publish_event(
                    "products.collections.completed",
                    {
                        "job_id": job_id,
                        "event_id": event_id
                    },
                    correlation_id=job_id
                )
                
                # Emit products images ready batch event with total_images: 0
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
                
                # Skip individual image events when no products found
                logger.info("Skipping individual image events for job with no products", job_id=job_id)
                
            else:
                # Emit products collections completed event
                event_id = str(uuid.uuid4())
                await self.broker.publish_event(
                    "products.collections.completed",
                    {
                        "job_id": job_id,
                        "event_id": event_id
                    },
                    correlation_id=job_id
                )
                
                # Emit products images ready batch event FIRST (before individual events)
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
                
                # Now publish individual image ready events
                await self.publish_individual_image_events(job_id)
                
                logger.info("Completed product collection",
                           job_id=job_id,
                           amazon_count=amazon_count,
                           ebay_count=ebay_count,
                           total_images=total_images)
            
        except Exception as e:
            logger.error("Failed to process product collection request", error=str(e))
            raise
    
    async def store_product(self, product_data: Dict[str, Any], job_id: str, source: str):
        """Store a single product and its images without publishing individual events"""
        try:
            # Create product record
            product = Product(
                product_id=str(uuid.uuid4()),
                src=source,
                asin_or_itemid=product_data["id"],
                title=product_data["title"],
                brand=product_data.get("brand"),
                url=product_data["url"]
            )
            
            # Save to database
            await self.db.execute(
                "INSERT INTO products (product_id, src, asin_or_itemid, title, brand, url, job_id) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                product.product_id, product.src, product.asin_or_itemid, 
                product.title, product.brand, product.url, job_id
            )
            
            # Process images (store only, don't publish events yet)
            for i, image_url in enumerate(product_data["images"]):
                image_id = f"{product.product_id}_img_{i}"
                local_path = await self.collectors[source].download_image(image_url, product.product_id, image_id)
                
                if local_path:
                    # Create image record
                    image = ProductImage(
                        img_id=image_id,
                        product_id=product.product_id,
                        local_path=local_path
                    )
                    
                    await self.image_crud.create_product_image(image)
            
            logger.info("Stored product", product_id=product.product_id, 
                       image_count=len(product_data["images"]))
            
        except Exception as e:
            logger.error("Failed to store product", product_data=product_data, error=str(e))
    
    async def publish_individual_image_events(self, job_id: str):
        """Publish individual image ready events for all images in a job"""
        try:
            # Get all images for this job
            images = await self.db.fetch_all(
                """
                SELECT pi.img_id, pi.product_id, pi.local_path
                FROM product_images pi
                JOIN products p ON pi.product_id = p.product_id
                WHERE p.job_id = $1
                ORDER BY pi.img_id
                """,
                job_id
            )
            
            logger.info("Publishing individual image events", job_id=job_id, image_count=len(images))
            
            # Publish individual image ready events
            for image in images:
                await self.broker.publish_event(
                    "products.image.ready",
                    {
                        "product_id": image["product_id"],
                        "image_id": image["img_id"],
                        "local_path": image["local_path"],
                        "job_id": job_id
                    },
                    correlation_id=job_id
                )
            
            logger.info("Published all individual image events", job_id=job_id, image_count=len(images))
            
        except Exception as e:
            logger.error("Failed to publish individual image events", job_id=job_id, error=str(e))
    
    async def process_product(self, product_data: Dict[str, Any], job_id: str, source: str):
        """Process a single product and its images (legacy method for backward compatibility)"""
        try:
            # Create product record
            product = Product(
                product_id=str(uuid.uuid4()),
                src=source,
                asin_or_itemid=product_data["id"],
                title=product_data["title"],
                brand=product_data.get("brand"),
                url=product_data["url"]
            )
            
            # Save to database
            await self.db.execute(
                "INSERT INTO products (product_id, src, asin_or_itemid, title, brand, url, job_id) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                product.product_id, product.src, product.asin_or_itemid, 
                product.title, product.brand, product.url, job_id
            )
            
            # Process images
            for i, image_url in enumerate(product_data["images"]):
                image_id = f"{product.product_id}_img_{i}"
                local_path = await self.collectors[source].download_image(image_url, product.product_id, image_id)
                
                if local_path:
                    # Create image record
                    image = ProductImage(
                        img_id=image_id,
                        product_id=product.product_id,
                        local_path=local_path
                    )
                    
                    await self.image_crud.create_product_image(image)
                    
                    # Emit image ready event
                    await self.broker.publish_event(
                        "products.image.ready",
                        {
                            "product_id": product.product_id,
                            "image_id": image_id,
                            "local_path": local_path,
                            "job_id": job_id
                        },
                        correlation_id=job_id
                    )
            
            logger.info("Processed product", product_id=product.product_id, 
                       image_count=len(product_data["images"]))
            
        except Exception as e:
            logger.error("Failed to process product", product_data=product_data, error=str(e))
    
    async def close(self):
        """Close all collectors"""
        for collector in self.collectors.values():
            await collector.close()