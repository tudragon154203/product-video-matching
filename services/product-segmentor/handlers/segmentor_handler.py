"""Event handlers for Product Segmentor Service."""

from .decorators import validate_event, handle_errors
from services.service import ProductSegmentorService
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.logging_config import configure_logging
from config_loader import config

logger = configure_logging("segmentor-handler")


class ProductSegmentorHandler:
    """Event handler for product segmentation operations."""
    
    def __init__(self):
        """Initialize the handler."""
        self.db = DatabaseManager(config.POSTGRES_DSN)
        self.broker = MessageBroker(config.BUS_BROKER)
        self.service = ProductSegmentorService(
            db=self.db,
            broker=self.broker,
            model_name=config.SEGMENTATION_MODEL_NAME,
            mask_base_path=config.MASK_BASE_PATH,
            max_concurrent=config.MAX_CONCURRENT_IMAGES
        )
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize the handler and service."""
        if not self.initialized:
            await self.service.initialize()
            self.initialized = True
            logger.info("Product Segmentor Handler initialized")
    
    async def cleanup(self) -> None:
        """Cleanup handler resources."""
        try:
            await self.service.cleanup()
            logger.info("Handler cleanup completed")
        except Exception as e:
            logger.error("Error during handler cleanup", error=str(e))
    
    @validate_event("products_image_ready")
    @handle_errors
    async def handle_products_image_ready(self, event_data: dict) -> None:
        """Handle product images ready event.
        
        Args:
            event_data: Event payload containing product image information
        """
        logger.info(
            "Received product image ready event", 
            product_id=event_data.get("product_id"),
            image_id=event_data.get("image_id")
        )
        
        await self.service.handle_products_image_ready(event_data)
    
    @validate_event("products_images_ready_batch")
    @handle_errors
    async def handle_products_images_ready_batch(self, event_data: dict) -> None:
        """Handle product images ready batch event.
        
        Args:
            event_data: Batch event payload
        """
        logger.info(
            "Received product images ready batch event",
            job_id=event_data.get("job_id"),
            total_images=event_data.get("total_images")
        )
        
        await self.service.handle_products_images_ready_batch(event_data)
    
    @validate_event("videos_keyframes_ready")
    @handle_errors
    async def handle_videos_keyframes_ready(self, event_data: dict) -> None:
        """Handle video keyframes ready event.
        
        Args:
            event_data: Event payload containing video keyframe information
        """
        logger.info(
            "Received video keyframes ready event",
            video_id=event_data.get("video_id"),
            frame_count=len(event_data.get("frames", []))
        )
        
        await self.service.handle_videos_keyframes_ready(event_data)
    
    @validate_event("videos_keyframes_ready_batch")
    @handle_errors
    async def handle_videos_keyframes_ready_batch(self, event_data: dict) -> None:
        """Handle video keyframes ready batch event.
        
        Args:
            event_data: Batch event payload
        """
        logger.info(
            "Received video keyframes ready batch event",
            job_id=event_data.get("job_id"),
            total_keyframes=event_data.get("total_keyframes")
        )
        
        await self.service.handle_videos_keyframes_ready_batch(event_data)