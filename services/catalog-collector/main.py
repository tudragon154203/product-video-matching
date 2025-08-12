import os
import asyncio
import uuid
import sys
sys.path.append('/app/libs')

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import ProductCRUD, ProductImageCRUD
from common_py.models import Product, ProductImage
from contracts.validator import validator
from collector import ProductCollector

# Configure logging
logger = configure_logging("catalog-collector")

# Environment variables
sys.path.append('/app/infra')
from config import config

POSTGRES_DSN = config.POSTGRES_DSN
BUS_BROKER = config.BUS_BROKER
DATA_ROOT = config.DATA_ROOT

# Global instances
db = DatabaseManager(POSTGRES_DSN)
broker = MessageBroker(BUS_BROKER)
product_crud = ProductCRUD(db)
image_crud = ProductImageCRUD(db)
collector = ProductCollector(DATA_ROOT)


async def handle_products_collect_request(event_data):
    """Handle products collection request"""
    try:
        # Validate event
        validator.validate_event("products_collect_request", event_data)
        
        job_id = event_data["job_id"]
        industry = event_data["industry"]
        top_amz = event_data["top_amz"]
        top_ebay = event_data["top_ebay"]
        
        logger.info("Processing product collection request", 
                   job_id=job_id, industry=industry)
        
        # Collect Amazon products
        amazon_products = await collector.collect_amazon_products(industry, top_amz)
        for product_data in amazon_products:
            await process_product(product_data, job_id, "amazon")
        
        # Collect eBay products
        ebay_products = await collector.collect_ebay_products(industry, top_ebay)
        for product_data in ebay_products:
            await process_product(product_data, job_id, "ebay")
        
        logger.info("Completed product collection", 
                   job_id=job_id, 
                   amazon_count=len(amazon_products),
                   ebay_count=len(ebay_products))
        
    except Exception as e:
        logger.error("Failed to process product collection request", error=str(e))
        raise


async def process_product(product_data, job_id, source):
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
        
        # Save to database (need to add job_id to the model)
        await db.execute(
            "INSERT INTO products (product_id, src, asin_or_itemid, title, brand, url, job_id) VALUES ($1, $2, $3, $4, $5, $6, $7)",
            product.product_id, product.src, product.asin_or_itemid, 
            product.title, product.brand, product.url, job_id
        )
        
        # Process images
        for i, image_url in enumerate(product_data["images"]):
            image_id = f"{product.product_id}_img_{i}"
            local_path = await collector.download_image(image_url, product.product_id, image_id)
            
            if local_path:
                # Create image record
                image = ProductImage(
                    img_id=image_id,
                    product_id=product.product_id,
                    local_path=local_path
                )
                
                await image_crud.create_product_image(image)
                
                # Emit image ready event
                await broker.publish_event(
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


async def main():
    """Main service loop"""
    try:
        # Initialize connections
        await db.connect()
        await broker.connect()
        
        # Subscribe to events
        await broker.subscribe_to_topic(
            "products.collect.request",
            handle_products_collect_request
        )
        
        logger.info("Catalog collector service started")
        
        # Keep service running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down catalog collector service")
    except Exception as e:
        logger.error("Service error", error=str(e))
    finally:
        await db.disconnect()
        await broker.disconnect()


if __name__ == "__main__":
    asyncio.run(main())