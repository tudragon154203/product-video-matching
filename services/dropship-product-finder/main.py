import asyncio
import sys
import os
from contextlib import asynccontextmanager

# Add the app directory to the Python path for bind mount setup
sys.path.append("/app/app")

from common_py.logging_config import configure_logging
from handlers.dropship_product_handler import DropshipProductHandler
from config_loader import config
import aioredis

logger = configure_logging("dropship-product-finder")

@asynccontextmanager
async def service_context():
    """Context manager for service resources"""
    handler = DropshipProductHandler()
    redis_client = None
    
    try:
        # Initialize connections
        await handler.db.connect()
        await handler.broker.connect()
        
        # Initialize Redis client
        redis_client = aioredis.from_url(config.REDIS_URL, decode_responses=True)
        await redis_client.ping()  # Test connection
        logger.info("Redis connection established")
        
        # Update handler with Redis client
        handler.redis = redis_client
        
        yield handler
        
    except Exception as e:
        logger.error("Failed to initialize service resources", error=str(e))
        raise
    finally:
        # Cleanup resources
        if redis_client:
            await redis_client.close()
            logger.info("Redis connection closed")
        await handler.db.disconnect()
        await handler.broker.disconnect()

async def main():
    """Main service loop"""
    try:
        async with service_context() as handler:
            # Subscribe to events
            await handler.broker.subscribe_to_topic(
                "products.collect.request",
                handler.handle_products_collect_request
            )
            
            logger.info("Product finder service started")
            
            # Keep service running
            while True:
                await asyncio.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Shutting down Dropship Product Finder service")
    except Exception as e:
        logger.error("Service error", error=str(e))

if __name__ == "__main__":
    asyncio.run(main())