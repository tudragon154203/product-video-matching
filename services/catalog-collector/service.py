import uuid
import structlog
from typing import Dict, Any, List
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import ProductCRUD, ProductImageCRUD
from common_py.models import Product, ProductImage
from collectors import BaseProductCollector, AmazonProductCollector, EbayProductCollector

logger = structlog.get_logger()


class CatalogCollectorService:
    """Main service class for catalog collection"""
    
    def __init__(self, db: DatabaseManager, broker: MessageBroker, data_root: str):
        self.db = db
        self.broker = broker
        self.product_crud = ProductCRUD(db)
        self.image_crud = ProductImageCRUD(db)
        
        # Initialize collectors
        self.collectors: Dict[str, BaseProductCollector] = {
            "amazon": AmazonProductCollector(data_root),
            "ebay": EbayProductCollector(data_root)
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
            
            # Collect Amazon products for each query
            for query in queries:
                amazon_products = await self.collectors["amazon"].collect_products(query, top_amz)
                for product_data in amazon_products:
                    await self.process_product(product_data, job_id, "amazon")
            
            # Collect eBay products for each query
            for query in queries:
                ebay_products = await self.collectors["ebay"].collect_products(query, top_ebay)
                for product_data in ebay_products:
                    await self.process_product(product_data, job_id, "ebay")
            
            logger.info("Completed product collection",
                       job_id=job_id,
                       amazon_count=len(amazon_products) if 'amazon_products' in locals() else 0,
                       ebay_count=len(ebay_products) if 'ebay_products' in locals() else 0)
            
        except Exception as e:
            logger.error("Failed to process product collection request", error=str(e))
            raise
    
    async def process_product(self, product_data: Dict[str, Any], job_id: str, source: str):
        """Process a single product and its images"""
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
                        "products.images.ready",
                        {
                            "product_id": product.product_id,
                            "image_id": image_id,
                            "local_path": local_path
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