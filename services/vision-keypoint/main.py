import asyncio
import sys
import os
from contextlib import asynccontextmanager

# Add the app directory to the Python path for bind mount setup
sys.path.append("/app/app")

from common_py.logging_config import configure_logging
from handlers.keypoint_handler import VisionKeypointHandler
from config_loader import config

logger = configure_logging("vision-keypoint")

@asynccontextmanager
async def service_context():
    """Context manager for service resources"""
    handler = VisionKeypointHandler()
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
            # Subscribe to events
            # Avoid competing with vision-embedding by setting queue_name
            await handler.broker.subscribe_to_topic(
                "products.images.ready.batch",
                handler.handle_products_images_ready_batch,
                queue_name="q.vision-keypoint.images.batch" 
            )

            await handler.broker.subscribe_to_topic(
                "videos.keyframes.ready.batch",
                handler.handle_videos_keyframes_ready_batch,
                queue_name="q.vision_keypoint.keyframes.batch"
            )
            
            await handler.broker.subscribe_to_topic(
                "products.images.ready",
                handler.handle_products_images_ready,
                queue_name="q.vision-keypoint.images.ready" 
            )
            
            await handler.broker.subscribe_to_topic(
                "videos.keyframes.ready",
                handler.handle_videos_keyframes_ready,
                queue_name="q.vision_keypoint.keyframes.ready"
            )
            
           
            
            logger.info("Vision keypoint service started")
            
            # Keep service running
            while True:
                await asyncio.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Shutting down vision keypoint service")
    except Exception as e:
        logger.error("Service error", error=str(e))

if __name__ == "__main__":
    asyncio.run(main())