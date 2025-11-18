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
        # Print configuration for debugging
        import os
        from config_loader import config
        print("Environment variables loaded:")
        print(f"  POSTGRES_HOST: {os.getenv('POSTGRES_HOST', 'NOT SET')}")
        print(f"  POSTGRES_PORT: {os.getenv('POSTGRES_PORT', 'NOT SET')}")
        print(f"  POSTGRES_USER: {os.getenv('POSTGRES_USER', 'NOT SET')}")
        print(f"  POSTGRES_DB: {os.getenv('POSTGRES_DB', 'NOT SET')}")
        print(f"  BUS_BROKER: {os.getenv('BUS_BROKER', 'NOT SET')}")
        print(f"Database DSN: {config.POSTGRES_DSN}")
        print(f"Broker URL: {config.BUS_BROKER}")

        async with service_context() as handler:
            # Subscribe to events
            # Per-job event: prefetch_count=1 (process one match request at a time)
            await handler.broker.subscribe_to_topic(
                "match.request",
                handler.handle_match_request,
                prefetch_count=1,
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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down matcher service")
    except Exception as e:
        logger.error("Service error", error=str(e))
        import traceback
        traceback.print_exc()
