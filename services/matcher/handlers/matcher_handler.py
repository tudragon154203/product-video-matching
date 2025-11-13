"""Event handler for matcher service operations."""

from typing import Any, Dict

from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker

from config_loader import config
from services.service import MatcherService

from .decorators import handle_errors, validate_event


class MatcherHandler:
    def __init__(self) -> None:
        self.db = DatabaseManager(config.POSTGRES_DSN)
        self.broker = MessageBroker(config.BUS_BROKER)
        self.service = MatcherService(
            self.db,
            self.broker,
            config.DATA_ROOT,
            retrieval_topk=config.RETRIEVAL_TOPK,
            sim_deep_min=config.SIM_DEEP_MIN,
            inliers_min=config.INLIERS_MIN,
            match_best_min=config.MATCH_BEST_MIN,
            match_cons_min=config.MATCH_CONS_MIN,
            match_accept=config.MATCH_ACCEPT,
        )
        self.initialized = False

    async def initialize(self) -> None:
        if not self.initialized:
            await self.service.initialize()
            self.initialized = True

    @handle_errors
    @validate_event("match_request")
    async def handle_match_request(self, event_data: Dict[str, Any], correlation_id: str) -> None:
        await self.service.handle_match_request(event_data)
