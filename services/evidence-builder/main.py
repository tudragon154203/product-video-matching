"""Entrypoint for the evidence builder microservice."""

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

try:
    from common_py.logging_config import configure_logging
except ModuleNotFoundError:  # pragma: no cover - defensive local setup
    repo_root = Path(__file__).resolve().parents[2]
    libs_path = repo_root / "libs"
    if str(libs_path) not in sys.path:
        sys.path.insert(0, str(libs_path))
    from common_py.logging_config import configure_logging

from handlers.evidence_handler import EvidenceHandler

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
    # We log and propagate unexpected errors so orchestration can restart us.
    except Exception as exc:  # noqa: BLE001
        logger.error("Service error", error=str(exc))


if __name__ == "__main__":
    asyncio.run(main())
