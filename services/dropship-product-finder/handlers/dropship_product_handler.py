from .decorators import validate_event, handle_errors
from services.service import DropshipProductFinderService
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from config_loader import config

class DropshipProductHandler:
    def __init__(self):
        self.db = DatabaseManager(config.POSTGRES_DSN)
        self.broker = MessageBroker(config.BUS_BROKER)
        self.service = DropshipProductFinderService(self.db, self.broker, config.DATA_ROOT)
        
    @handle_errors
    @validate_event("products_collect_request")
    async def handle_products_collect_request(self, event_data):
        await self.service.handle_products_collect_request(event_data)