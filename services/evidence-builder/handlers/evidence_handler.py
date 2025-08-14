from .decorators import handle_errors
from services.service import EvidenceBuilderService
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from config_loader import config

class EvidenceHandler:
    def __init__(self):
        self.db = DatabaseManager(config.POSTGRES_DSN)
        self.broker = MessageBroker(config.BUS_BROKER)
        self.service = EvidenceBuilderService(self.db, self.broker, config.DATA_ROOT)
        
    @handle_errors
    async def handle_match_result(self, event_data):
        await self.service.handle_match_result(event_data)