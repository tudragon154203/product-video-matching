"""Entrypoint for the evidence builder microservice."""

import asyncio
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

# Add the app directory to the Python path for bind mount setup
sys.path.append("/app/app")

from common_py.logging_config import configure_logging  # noqa: E402

from handlers.evidence_handler import EvidenceHandler  # noqa: E402

logger = configure_logging("evidence-builder:main")


@asynccontextmanager
async def service_context() -> AsyncIterator[EvidenceHandler]:
    """Context manager for service resources."""

    handler = EvidenceHandler()
    try:
        await handler.db.connect()
        await handler.broker.connect()
        yield handler
    finally:
        await handler.db.disconnect()
        await handler.broker.disconnect()


async def main() -> None:
    """Main service loop."""

    try:
        async with service_context() as handler:
            await handler.broker.subscribe_to_topic(
                "match.result",
                handler.handle_match_result,
            )
            await handler.broker.subscribe_to_topic(
                "matchings.process.completed",
                handler.handle_matchings_completed,
            )

            logger.info("Evidence builder service started")

            while True:
                await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down evidence builder service")
    except Exception as exc:  # noqa: BLE001
        logger.error("Service error", error=str(exc))


if __name__ == "__main__":
    asyncio.run(main())
