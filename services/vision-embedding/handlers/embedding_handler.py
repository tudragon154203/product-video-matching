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
        
    # New masked event handlers
    @validate_event("products_image_masked")
    async def handle_products_image_masked(self, event_data):
        """Handle product image masked event"""
        await self.service.handle_products_image_masked(event_data)
        
    @validate_event("video_keyframes_masked")
    async def handle_video_keyframes_masked(self, event_data):
        """Handle video keyframes masked event"""
        await self.service.handle_video_keyframes_masked(event_data)
    
    @validate_event("products_images_masked_batch")
    async def handle_products_images_masked_batch(self, event_data):
        """Handle products images masked batch event"""
        await self.service.handle_products_images_masked_batch(event_data)
    
    @validate_event("video_keyframes_masked_batch")
    async def handle_videos_keyframes_masked_batch(self, event_data):
        """Handle videos keyframes masked batch event"""
        await self.service.handle_videos_keyframes_masked_batch(event_data)