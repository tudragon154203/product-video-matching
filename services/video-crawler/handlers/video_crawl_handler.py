from .decorators import validate_event, handle_errors
from services.service import VideoCrawlerService
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from config_loader import config

class VideoCrawlHandler:
    def __init__(self):
        self.db = DatabaseManager(config.POSTGRES_DSN)
        self.broker = MessageBroker(config.BUS_BROKER)
        self.service = VideoCrawlerService(self.db, self.broker, config.DATA_ROOT)
        
    @handle_errors
    @validate_event("videos_search_request")
    async def handle_videos_search_request(self, event_data):
        await self.service.handle_videos_search_request(event_data)