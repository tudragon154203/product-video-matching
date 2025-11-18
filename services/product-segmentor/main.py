"""Main entry point for Product Segmentor Service."""

from handlers.segmentor_handler import ProductSegmentorHandler
from common_py.logging_config import configure_logging
import asyncio
import sys
from contextlib import asynccontextmanager

# Add the app directory to the Python path for bind mount setup
sys.path.append("/app/app")


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
            from config_loader import config
            
            # Subscribe to product image events
            # Batch events: prefetch_count=1 (process one batch at a time)
            await handler.broker.subscribe_to_topic(
                "products.images.ready.batch",
                handler.handle_products_images_ready_batch,
                prefetch_count=1,
            )

            # Per-asset events: allow parallel processing up to MAX_CONCURRENT_BATCHES
            await handler.broker.subscribe_to_topic(
                "products.image.ready",
                handler.handle_products_image_ready,
                prefetch_count=config.MAX_CONCURRENT_BATCHES
            )

            # Subscribe to video keyframe events
            # Batch events: prefetch_count=1 (process one batch at a time)
            await handler.broker.subscribe_to_topic(
                "videos.keyframes.ready.batch",
                handler.handle_videos_keyframes_ready_batch,
                prefetch_count=1,
            )

            # Per-asset events: allow parallel processing up to MAX_CONCURRENT_BATCHES
            await handler.broker.subscribe_to_topic(
                "videos.keyframes.ready",
                handler.handle_videos_keyframes_ready,
                prefetch_count=config.MAX_CONCURRENT_BATCHES
            )

            logger.info(
                "Product Segmentor Service started",
                max_concurrent_batches=config.MAX_CONCURRENT_BATCHES,
                max_concurrent_images_in_batch=config.MAX_CONCURRENT_IMAGES_IN_BATCH
            )

            # Keep service running
            while True:
                await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down Product Segmentor Service")
    except Exception as e:
        logger.error("Service error", error=str(e))


if __name__ == "__main__":
    asyncio.run(main())
