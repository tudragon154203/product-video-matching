from handlers.keypoint_handler import VisionKeypointHandler
from common_py.logging_config import configure_logging
import asyncio
import sys
from contextlib import asynccontextmanager

# Add the app directory to the Python path for bind mount setup
sys.path.append("/app/app")


logger = configure_logging("vision-keypoint:main")


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
            # Subscribe to masked events (new segmentation pipeline)
            await handler.broker.subscribe_to_topic(
                "products.images.masked.batch",
                handler.handle_products_images_masked_batch,
                queue_name="q.vision-keypoint.images.masked.batch"
            )

            await handler.broker.subscribe_to_topic(
                "video.keyframes.masked.batch",
                handler.handle_videos_keyframes_masked_batch,
                queue_name="q.vision_keypoint.keyframes.masked.batch"
            )

            await handler.broker.subscribe_to_topic(
                "products.image.masked",
                handler.handle_products_image_masked,
                queue_name="q.vision-keypoint.image.masked"
            )

            await handler.broker.subscribe_to_topic(
                "video.keyframes.masked",
                handler.handle_video_keyframes_masked,
                queue_name="q.vision_keypoint.keyframes.masked"
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
