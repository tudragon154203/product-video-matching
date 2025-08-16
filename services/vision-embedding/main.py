import asyncio
import sys
import os
from contextlib import asynccontextmanager

# Add the app directory to the Python path for bind mount setup
sys.path.append("/app/app")

from common_py.logging_config import configure_logging
from handlers.embedding_handler import VisionEmbeddingHandler
from config_loader import config

logger = configure_logging("vision-embedding")

@asynccontextmanager
async def service_context():
    """Context manager for service resources"""
    handler = VisionEmbeddingHandler()
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
    """Main service loop"""
    try:
        async with service_context() as handler:
            # Subscribe to masked events (new segmentation pipeline)
            await handler.broker.subscribe_to_topic(
                "products.images.masked.batch",
                handler.handle_products_images_masked_batch,
                queue_name="q.vision-embedding.images.masked.batch"
            )

            await handler.broker.subscribe_to_topic(
                "video.keyframes.masked.batch",
                handler.handle_videos_keyframes_masked_batch,
                queue_name="q.vision_embedding.keyframes.masked.batch"
            )
            
            await handler.broker.subscribe_to_topic(
                "products.image.masked",
                handler.handle_products_image_masked,
                queue_name="q.vision_embedding.image.masked"
            )
            
            await handler.broker.subscribe_to_topic(
                "video.keyframes.masked",
                handler.handle_video_keyframes_masked,
                queue_name="q.vision_embedding.keyframes.masked"
            )
            
            logger.info("Vision embedding service started")
            
            # Keep service running
            while True:
                await asyncio.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Shutting down vision embedding service")
    except Exception as e:
        logger.error("Service error", error=str(e))

if __name__ == "__main__":
    asyncio.run(main())