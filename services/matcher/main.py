from handlers.matcher_handler import MatcherHandler
from common_py.logging_config import configure_logging
import asyncio
import sys
from contextlib import asynccontextmanager

# Add the app directory to the Python path for bind mount setup
sys.path.append("/app/app")


logger = configure_logging("matcher:main")


@asynccontextmanager
async def service_context():
    """Context manager for service resources"""
    handler = MatcherHandler()
    try:
        # Initialize connections
        await handler.db.connect()
        await handler.broker.connect()
        await handler.initialize()
        yield handler
    finally:
        # Cleanup resources
        await handler.service.cleanup()
        await handler.db.disconnect()
        await handler.broker.disconnect()


async def main():
    """Main service loop"""
    try:
        async with service_context() as handler:
            # Subscribe to events
            await handler.broker.subscribe_to_topic(
                "match.request",
                handler.handle_match_request
            )

            logger.info("Matcher service started")

            # Keep service running
            while True:
                await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down matcher service")
    except Exception as e:
        logger.error("Service error", error=str(e))

if __name__ == "__main__":
    asyncio.run(main())
