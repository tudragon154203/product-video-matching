from .decorators import validate_event, handle_errors
from services.service import VisionEmbeddingService
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from config_loader import config

class VisionEmbeddingHandler:
    def __init__(self):
        self.db = DatabaseManager(config.POSTGRES_DSN)
        self.broker = MessageBroker(config.BUS_BROKER)
        self.service = VisionEmbeddingService(self.db, self.broker, config.EMBED_MODEL)
        self.initialized = False
        
    async def initialize(self):
        if not self.initialized:
            await self.service.initialize()
            self.initialized = True
        
    @validate_event("products_images_ready")
    async def handle_products_images_ready(self, event_data):
        """Handle product images ready event"""
        await self.service.handle_products_images_ready(event_data)
        
    @validate_event("videos_keyframes_ready")
    async def handle_videos_keyframes_ready(self, event_data):
        """Handle video keyframes ready event"""
        await self.service.handle_videos_keyframes_ready(event_data)
    
    @validate_event("products_images_ready_batch")
    async def handle_products_images_ready_batch(self, event_data):
        """Handle products images ready batch event"""
        await self.service.handle_products_images_ready_batch(event_data)
    
    @validate_event("videos_keyframes_ready_batch")
    async def handle_videos_keyframes_ready_batch(self, event_data):
        """Handle videos keyframes ready batch event"""
        await self.service.handle_videos_keyframes_ready_batch(event_data)