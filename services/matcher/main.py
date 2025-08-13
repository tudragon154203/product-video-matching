import os
import asyncio
import sys

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from contracts.validator import validator
from service import MatcherService

# Configure logging
logger = configure_logging("matcher")

# Environment variables
from config_loader import config

POSTGRES_DSN = config.POSTGRES_DSN
BUS_BROKER = config.BUS_BROKER
DATA_ROOT = config.DATA_ROOT

# Matching parameters
RETRIEVAL_TOPK = config.RETRIEVAL_TOPK
SIM_DEEP_MIN = config.SIM_DEEP_MIN
INLIERS_MIN = config.INLIERS_MIN
MATCH_BEST_MIN = config.MATCH_BEST_MIN
MATCH_CONS_MIN = config.MATCH_CONS_MIN
MATCH_ACCEPT = config.MATCH_ACCEPT

# Global instances
db = DatabaseManager(POSTGRES_DSN)
broker = MessageBroker(BUS_BROKER)
service = MatcherService(
    db, broker, DATA_ROOT,
    retrieval_topk=RETRIEVAL_TOPK,
    sim_deep_min=SIM_DEEP_MIN,
    inliers_min=INLIERS_MIN,
    match_best_min=MATCH_BEST_MIN,
    match_cons_min=MATCH_CONS_MIN,
    match_accept=MATCH_ACCEPT
)


async def handle_match_request(event_data):
    """Handle match request event"""
    try:
        # Validate event
        validator.validate_event("match_request", event_data)
        await service.handle_match_request(event_data)
    except Exception as e:
        logger.error("Failed to process match request", error=str(e))
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
            "match.request",
            handle_match_request
        )
        
        logger.info("Matcher service started")
        
        # Keep service running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down matcher service")
    except Exception as e:
        logger.error("Service error", error=str(e))
    finally:
        await service.cleanup()
        await db.disconnect()
        await broker.disconnect()


if __name__ == "__main__":
    asyncio.run(main())