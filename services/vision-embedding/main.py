import os
import asyncio
import sys

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from contracts.validator import validator
from service import VisionEmbeddingService

# Configure logging
logger = configure_logging("vision-embedding")

# Environment variables
from config_loader import config

POSTGRES_DSN = config.POSTGRES_DSN
BUS_BROKER = config.BUS_BROKER
EMBED_MODEL = config.EMBED_MODEL

# Global instances
db = DatabaseManager(POSTGRES_DSN)
broker = MessageBroker(BUS_BROKER)
service = VisionEmbeddingService(db, broker, EMBED_MODEL)


async def handle_products_images_ready(event_data):
    """Handle product images ready event"""
    try:
        # Validate event
        validator.validate_event("products_images_ready", event_data)
        await service.handle_products_images_ready(event_data)
    except Exception as e:
        logger.error("Failed to process product image", error=str(e))
        raise


async def handle_videos_keyframes_ready(event_data):
    """Handle video keyframes ready event"""
    try:
        # Validate event
        validator.validate_event("videos_keyframes_ready", event_data)
        await service.handle_videos_keyframes_ready(event_data)
    except Exception as e:
        logger.error("Failed to process video frames", error=str(e))
        raise


async def main():
    """Main service loop"""
    try:
        # Initialize connections
        await db.connect()
        await broker.connect()
        await service.initialize()
        
        # Subscribe to events
        await broker.subscribe_to_topic(
            "products.images.ready",
            handle_products_images_ready
        )
        
        await broker.subscribe_to_topic(
            "videos.keyframes.ready",
            handle_videos_keyframes_ready
        )
        
        logger.info("Vision embedding service started")
        
        # Keep service running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down vision embedding service")
    except Exception as e:
        logger.error("Service error", error=str(e))
    finally:
        await service.cleanup()
        await db.disconnect()
        await broker.disconnect()


if __name__ == "__main__":
    asyncio.run(main())