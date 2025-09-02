"""Main entry point for Product Segmentor Service."""

import asyncio
import sys
import os
from contextlib import asynccontextmanager

# Add the app directory to the Python path for bind mount setup
sys.path.append("/app/app")

from common_py.logging_config import configure_logging
from handlers.segmentor_handler import ProductSegmentorHandler
from config_loader import config

logger = configure_logging("product-segmentor:main")


@asynccontextmanager
async def service_context():
    """Context manager for service resources."""
    handler = ProductSegmentorHandler()
    try:
        # Initialize connections
        await handler.db.connect()
        await handler.broker.connect()
        await handler.initialize()
        yield handler
    finally:
        # Cleanup resources
        await handler.broker.disconnect()
        await handler.db.disconnect()


async def main():
    """Main service loop."""
    try:
        async with service_context() as handler:
            # Subscribe to product image events
            await handler.broker.subscribe_to_topic(
                "products.images.ready.batch",
                handler.handle_products_images_ready_batch,
            )
            
            await handler.broker.subscribe_to_topic(
                "products.image.ready",
                handler.handle_products_image_ready,
            )
            
            # Subscribe to video keyframe events
            await handler.broker.subscribe_to_topic(
                "videos.keyframes.ready.batch",
                handler.handle_videos_keyframes_ready_batch,
            )
            
            await handler.broker.subscribe_to_topic(
                "videos.keyframes.ready",
                handler.handle_videos_keyframes_ready,
            )
            
            logger.info("Product Segmentor Service started")
            
            # Keep service running
            while True:
                await asyncio.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Shutting down Product Segmentor Service")
    except Exception as e:
        logger.error("Service error", error=str(e))


if __name__ == "__main__":
    asyncio.run(main())
