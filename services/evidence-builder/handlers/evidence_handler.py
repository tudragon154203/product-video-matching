"""Event handler entry points for the evidence builder service."""

from typing import Any, Dict

from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker

from config_loader import config
from services.service import EvidenceBuilderService

from .decorators import handle_errors, validate_event


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
    @validate_event("match_result")
    async def handle_match_result(
        self,
        event_data: Dict[str, Any],
        correlation_id: str,
    ) -> None:
        await self.service.handle_match_result(event_data, correlation_id)

    @handle_errors
    @validate_event("match_request_completed")
    async def handle_match_request_completed(
        self,
        event_data: Dict[str, Any],
        correlation_id: str,
    ) -> None:
        await self.service.handle_match_request_completed(event_data, correlation_id)
