from common_py.logging_config import configure_logging
from typing import Dict, Any, List, Optional
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import ProductImageCRUD, VideoFrameCRUD
from embedding import EmbeddingExtractor
import uuid
import asyncio
from vision_common import JobProgressManager
from services.asset_embedding_processor import AssetEmbeddingProcessor

logger = configure_logging("vision-embedding.services")


class VisionEmbeddingService:
    """Main service class for vision embedding with progress tracking"""
    
    def __init__(self, db: DatabaseManager, broker: MessageBroker, embed_model: str):
        self.db = db
        self.broker = broker
        self.image_crud = ProductImageCRUD(db)
        self.frame_crud = VideoFrameCRUD(db)
        logger.info("Initializing vision embedding service", model_name=embed_model)
        if hasattr(self.frame_crud, 'get_by_id'):
            logger.debug("VideoFrameCRUD has get_by_id method")
        else:
            logger.warning("VideoFrameCRUD does not have get_by_id method")
        self.extractor = EmbeddingExtractor(embed_model)
        self.progress_manager = JobProgressManager(broker)
        self.asset_embedding_processor = AssetEmbeddingProcessor(
            extractor=self.extractor,
            image_crud=self.image_crud,
            frame_crud=self.frame_crud,
            broker=self.broker,
            progress_manager=self.progress_manager
        )
    
    def _mark_batch_initialized(self, job_id: str, asset_type: str):
        self.progress_manager._mark_batch_initialized(job_id, asset_type)
    
    def _is_batch_initialized(self, job_id: str, asset_type: str) -> bool:
        return self.progress_manager._is_batch_initialized(job_id, asset_type)
    
    def _cleanup_job_tracking(self, job_id: str):
        self.progress_manager._cleanup_job_tracking(job_id)
    
    async def initialize(self):
        """Initialize the embedding extractor"""
        await self.extractor.initialize()
    
    async def cleanup(self):
        """Clean up resources"""
        await self.extractor.cleanup()
        await self.progress_manager.cleanup_all()
    
    async def _start_watermark_timer(self, job_id: str, ttl: int = 300):
        await self.progress_manager._start_watermark_timer(job_id, ttl, "embeddings")
    
    async def _publish_completion_event(self, job_id: str, is_timeout: bool = False):
        await self.progress_manager._publish_completion_event(job_id, is_timeout, "embeddings")
    
    async def _update_job_progress(self, job_id: str, asset_type: str, expected_count: int, increment: int = 1):
        await self.progress_manager.update_job_progress(job_id, asset_type, expected_count, increment, "embeddings")
    
    async def handle_products_images_ready_batch(self, event_data: Dict[str, Any]):
        """Handle products images ready batch event to initialize job tracking"""
        await self.asset_embedding_processor.handle_products_images_ready_batch(event_data)
    
    async def handle_videos_keyframes_ready_batch(self, event_data: Dict[str, Any]):
        """Handle videos keyframes ready batch event to initialize job tracking"""
        await self.asset_embedding_processor.handle_videos_keyframes_ready_batch(event_data)
    
    async def handle_products_image_ready(self, event_data: Dict[str, Any]):
        """Handle product images ready event"""
        await self.asset_embedding_processor.handle_products_image_ready(event_data)
    
    async def handle_videos_keyframes_ready(self, event_data: Dict[str, Any]):
        """Handle video keyframes ready event"""
        await self.asset_embedding_processor.handle_videos_keyframes_ready(event_data)
    
    async def handle_products_image_masked(self, event_data: Dict[str, Any]):
        """Handle product image masked event"""
        await self.asset_embedding_processor.handle_products_image_masked(event_data)

    async def handle_video_keyframes_masked(self, event_data: Dict[str, Any]):
        """Handle video keyframes masked event"""
        await self.asset_embedding_processor.handle_video_keyframes_masked(event_data)
