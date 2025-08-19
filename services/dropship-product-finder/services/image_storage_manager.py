import uuid
from typing import Dict, Any, List
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import ProductCRUD, ProductImageCRUD
from common_py.models import Product, ProductImage
from common_py.logging_config import configure_logging
from collectors.base_product_collector import BaseProductCollector

logger = configure_logging("dropship-product-finder")

class ImageStorageManager:
    def __init__(self, db: DatabaseManager, broker: MessageBroker, collectors: Dict[str, BaseProductCollector]):
        self.db = db
        self.broker = broker
        self.product_crud = ProductCRUD(db)
        self.image_crud = ProductImageCRUD(db)
        self.collectors = collectors

    async def store_product(self, product_data: Dict[str, Any], job_id: str, source: str):
        """Store a single product and its images without publishing individual events"""
        try:
            product = Product(
                product_id=str(uuid.uuid4()),
                src=source,
                asin_or_itemid=product_data["id"],
                title=product_data["title"],
                brand=product_data.get("brand"),
                url=product_data["url"]
            )
            
            await self.db.execute(
                "INSERT INTO products (product_id, src, asin_or_itemid, title, brand, url, job_id) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                product.product_id, product.src, product.asin_or_itemid, 
                product.title, product.brand, product.url, job_id
            )
            
            await self._download_and_store_product_images(product, product_data["images"], source)
            
            logger.info("Stored product", product_id=product.product_id, 
                       image_count=len(product_data["images"]))
            
        except Exception as e:
            logger.error("Failed to store product", product_data=product_data, error=str(e))

    async def _download_and_store_product_images(self, product: Product, image_urls: List[str], source: str):
        try:
            for i, image_url in enumerate(image_urls):
                image_id = f"{product.product_id}_img_{i}"
                local_path = await self.collectors[source].download_image(image_url, product.product_id, image_id)
                
                if local_path:
                    image = ProductImage(
                        img_id=image_id,
                        product_id=product.product_id,
                        local_path=local_path
                    )
                    
                    await self.image_crud.create_product_image(image)
                
                logger.info("Stored product", product_id=product.product_id,
                           image_count=len(image_urls)) # Corrected to image_urls length
        
        except Exception as e:
            logger.error("Failed to store product image", product_id=product.product_id, image_url=image_url, error=str(e))

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
