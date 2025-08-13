from .decorators import validate_event, handle_errors
from services.service import VectorIndexService
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from config_loader import config

class VectorIndexHandler:
    def __init__(self):
        self.db = DatabaseManager(config.POSTGRES_DSN)
        self.broker = MessageBroker(config.BUS_BROKER)
        self.service = VectorIndexService(self.db, self.broker)
        self.initialized = False
        
    @validate_event("features_ready")
    async def handle_features_ready(self, event_data):
        """Handle features ready event"""
        await self.service.handle_features_ready(event_data)