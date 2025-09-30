from config_loader import config
from handlers.video_crawl_handler import VideoCrawlHandler
from common_py.logging_config import configure_logging
import asyncio
import sys
from contextlib import asynccontextmanager

# Add the app directory to the Python path for bind mount setup
sys.path.append("/app/app")


logger = configure_logging("video-crawler:main", log_level=config.LOG_LEVEL)


@asynccontextmanager
async def service_context():
    """Context manager for service resources"""
    handler = VideoCrawlHandler()
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
                "videos.search.request",
                handler.handle_videos_search_request
            )

            logger.info("Video crawler service started")

            # Keep service running
            while True:
                await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down Video Crawler service")
    except Exception as e:
        logger.error("Service error", error=str(e))

if __name__ == "__main__":
    asyncio.run(main())
