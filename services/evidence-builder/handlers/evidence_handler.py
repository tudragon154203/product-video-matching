"""Event handler entry points for the evidence builder service."""

from typing import Any, Dict

from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker

from config_loader import config
from services.service import EvidenceBuilderService

from .decorators import handle_errors


class EvidenceHandler:
    """Expose event-specific handler methods."""

    def __init__(self) -> None:
        self.db = DatabaseManager(config.POSTGRES_DSN)
        self.broker = MessageBroker(config.BUS_BROKER)
        self.service = EvidenceBuilderService(
            self.db,
            self.broker,
            config.DATA_ROOT,
        )

    @handle_errors
    async def handle_match_result(self, event_data: Dict[str, Any]) -> None:
        await self.service.handle_match_result(event_data)

    @handle_errors
    async def handle_matchings_completed(self, event_data: Dict[str, Any]) -> None:
        await self.service.handle_matchings_completed(event_data)
