from .decorators import validate_event, handle_errors
from services.service import DropshipProductFinderService
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from config_loader import config
from typing import Any
from common_py.logging_config import configure_logging

logger = configure_logging("dropship-product-finder:handler")


class DropshipProductHandler:
    def __init__(self, redis_client=None):
        self.db = DatabaseManager(config.POSTGRES_DSN)
        self.broker = MessageBroker(config.BUS_BROKER)
        self.redis = redis_client
        self.service = DropshipProductFinderService(
            self.db, self.broker, config.DATA_ROOT, self.redis
        )

    def update_redis_client(self, redis_client: Any) -> None:
        """Update the Redis client for the handler and the internal service."""
        self.redis = redis_client
        self.service.update_redis_client(redis_client)
        logger.info("DropshipProductHandler Redis client updated")

    @handle_errors
    @validate_event("products_collect_request")
    async def handle_products_collect_request(self, event_data):
        await self.service.handle_products_collect_request(event_data)
