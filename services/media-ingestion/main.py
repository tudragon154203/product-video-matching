import os
import asyncio
import sys

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from contracts.validator import validator
from service import MediaIngestionService

# Configure logging
logger = configure_logging("media-ingestion")

# Environment variables
from config_loader import config

POSTGRES_DSN = config.POSTGRES_DSN
BUS_BROKER = config.BUS_BROKER
DATA_ROOT = config.DATA_ROOT

# Global instances
db = DatabaseManager(POSTGRES_DSN)
broker = MessageBroker(BUS_BROKER)
service = MediaIngestionService(db, broker, DATA_ROOT)


async def handle_videos_search_request(event_data):
    """Handle video search request"""
    try:
        # Validate event
        validator.validate_event("videos_search_request", event_data)
        await service.handle_videos_search_request(event_data)
    except Exception as e:
        logger.error("Failed to process video search request", error=str(e))
        raise


async def main():
    """Main service loop"""
    try:
        # Initialize connections
        await db.connect()
        await broker.connect()
        
        # Subscribe to events
        await broker.subscribe_to_topic(
            "videos.search.request",
            handle_videos_search_request
        )
        
        logger.info("Media ingestion service started")
        
        # Keep service running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down media ingestion service")
    except Exception as e:
        logger.error("Service error", error=str(e))
    finally:
        await db.disconnect()
        await broker.disconnect()


if __name__ == "__main__":
    asyncio.run(main())