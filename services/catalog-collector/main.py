import asyncio
import sys
import os
from contextlib import asynccontextmanager

# Add the app directory to the Python path for bind mount setup
sys.path.append("/app/app")

from common_py.logging_config import configure_logging
from handlers.product_handler import ProductHandler
from config_loader import config

logger = configure_logging("catalog-collector")

@asynccontextmanager
async def service_context():
    """Context manager for service resources"""
    handler = ProductHandler()
    try:
        # Initialize connections
        await handler.db.connect()
        await handler.broker.connect()
        yield handler
    finally:
        # Cleanup resources
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
            
            logger.info("Catalog collector service started")
            
            # Keep service running
            while True:
                await asyncio.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Shutting down catalog collector service")
    except Exception as e:
        logger.error("Service error", error=str(e))

if __name__ == "__main__":
    asyncio.run(main())