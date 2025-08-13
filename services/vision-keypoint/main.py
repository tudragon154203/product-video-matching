import os
import asyncio
import sys

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from contracts.validator import validator
from service import VisionKeypointService

# Configure logging
logger = configure_logging("vision-keypoint")

# Environment variables
from config_loader import config

POSTGRES_DSN = config.POSTGRES_DSN
BUS_BROKER = config.BUS_BROKER
DATA_ROOT = config.DATA_ROOT

# Global instances
db = DatabaseManager(POSTGRES_DSN)
broker = MessageBroker(BUS_BROKER)
service = VisionKeypointService(db, broker, DATA_ROOT)


async def handle_products_images_ready(event_data):
    """Handle product images ready event"""
    try:
        # Validate event
        validator.validate_event("products_images_ready", event_data)
        await service.handle_products_images_ready(event_data)
    except Exception as e:
        logger.error("Failed to process product image keypoints", error=str(e))
        raise


async def handle_videos_keyframes_ready(event_data):
    """Handle video keyframes ready event"""
    try:
        # Validate event
        validator.validate_event("videos_keyframes_ready", event_data)
        await service.handle_videos_keyframes_ready(event_data)
    except Exception as e:
        logger.error("Failed to process video frame keypoints", error=str(e))
        raise


async def main():
    """Main service loop"""
    try:
        # Initialize connections
        await db.connect()
        await broker.connect()
        
        # Subscribe to events
        await broker.subscribe_to_topic(
            "products.images.ready",
            handle_products_images_ready
        )
        
        await broker.subscribe_to_topic(
            "videos.keyframes.ready",
            handle_videos_keyframes_ready
        )
        
        logger.info("Vision keypoint service started")
        
        # Keep service running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down vision keypoint service")
    except Exception as e:
        logger.error("Service error", error=str(e))
    finally:
        await db.disconnect()
        await broker.disconnect()


if __name__ == "__main__":
    asyncio.run(main())