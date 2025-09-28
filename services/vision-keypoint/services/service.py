from typing import Any, Dict

from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging
from common_py.messaging import MessageBroker

from keypoint import KeypointExtractor
from vision_common import JobProgressManager

from .keypoint_asset_processor import KeypointAssetProcessor

logger = configure_logging("vision-keypoint:service")


class VisionKeypointService:
    """Main service class for vision keypoint extraction with progress tracking"""
    
    def __init__(
        self, db: DatabaseManager, broker: MessageBroker, data_root: str
    ):
        self.db = db
        self.broker = broker
        self.extractor = KeypointExtractor(data_root)
        self.progress_manager = JobProgressManager(broker)
        self.asset_processor = KeypointAssetProcessor(
            db, broker, self.extractor, self.progress_manager
        )
    
    async def cleanup(self):
        """Clean up resources"""
        await self.progress_manager.cleanup_all()
    
    async def handle_products_image_ready(self, event_data: Dict[str, Any]):
        """Handle product images ready event"""
        try:
            job_id = event_data["job_id"]
            image_id = event_data["image_id"]
            local_path = event_data["local_path"]

            update_progress = (
                self.asset_processor.update_and_check_completion_per_asset_first
            )

            success = await self.asset_processor.process_single_asset(
                job_id,
                image_id,
                "image",
                local_path,
            )

            if success:
                await update_progress(job_id, "image")

        except Exception as e:
            logger.error(
                "Item processing failed",
                job_id=job_id,
                asset_id=image_id,
                asset_type="image",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    async def handle_videos_keyframes_ready(self, event_data: Dict[str, Any]):
        """Handle video keyframes ready event"""
        try:
            job_id = event_data["job_id"]
            frames = event_data["frames"]

            update_progress = (
                self.asset_processor.update_and_check_completion_per_asset_first
            )

            for frame_data in frames:
                frame_id = frame_data["frame_id"]
                local_path = frame_data["local_path"]
                
                success = await self.asset_processor.process_single_asset(
                    job_id,
                    frame_id,
                    "video",
                    local_path,
                )

                if success:
                    await update_progress(job_id, "video")

        except Exception as e:
            logger.error(
                "Batch processing failed",
                job_id=job_id,
                asset_type="video",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def handle_products_image_masked(self, event_data: Dict[str, Any]):
        """Handle product image masked event"""
        try:
            job_id = event_data["job_id"]
            image_id = event_data["image_id"]
            mask_path = event_data["mask_path"]

            update_progress = (
                self.asset_processor.update_and_check_completion_per_asset_first
            )
            
            success = await self.asset_processor.process_single_asset(
                job_id,
                image_id,
                "image",
                None,
                is_masked=True,
                mask_path=mask_path,
            )

            if success:
                await update_progress(job_id, "image")

        except Exception as e:
            logger.error(
                "Item processing failed",
                job_id=job_id,
                asset_id=image_id,
                asset_type="image",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def handle_video_keyframes_masked(self, event_data: Dict[str, Any]):
        """Handle video keyframes masked event"""
        try:
            job_id = event_data["job_id"]
            frames = event_data["frames"]

            update_progress = (
                self.asset_processor.update_and_check_completion_per_asset_first
            )
            
            for frame_data in frames:
                frame_id = frame_data["frame_id"]
                mask_path = frame_data["mask_path"]
                
                success = await self.asset_processor.process_single_asset(
                    job_id,
                    frame_id,
                    "video",
                    None,
                    is_masked=True,
                    mask_path=mask_path,
                )

                if success:
                    await update_progress(job_id, "video")

        except Exception as e:
            logger.error(
                "Batch processing failed",
                job_id=job_id,
                asset_type="video",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def handle_products_images_masked_batch(self, event_data: Dict[str, Any]):
        """Handle products images masked batch event to initialize job tracking"""
        try:
            job_id = event_data["job_id"]
            total_images = event_data["total_images"]
            
            await self.asset_processor.handle_batch_initialization(
                job_id,
                "image",
                total_images,
                "products_images_masked_batch",
            )

        except Exception as e:
            logger.error(
                "Failed to handle products images masked batch",
                job_id=job_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def handle_videos_keyframes_masked_batch(self, event_data: Dict[str, Any]):
        """Handle videos keyframes masked batch event to initialize job tracking"""
        try:
            job_id = event_data["job_id"]
            event_id = event_data["event_id"]
            total_keyframes = event_data["total_keyframes"]
            
            # Create a unique identifier for this batch event to detect duplicates
            batch_event_key = f"{job_id}:{event_id}"
            
            # Check if we've already processed this batch event
            if batch_event_key in self.progress_manager.processed_batch_events:
                logger.info(
                    "Ignoring duplicate batch event",
                    job_id=job_id,
                    event_id=event_id,
                    asset_type="video",
                )
                return
            
            # Mark this batch event as processed
            self.progress_manager.processed_batch_events.add(batch_event_key)
            
            await self.asset_processor.handle_batch_initialization(
                job_id,
                "video",
                total_keyframes,
                "videos_keyframes_masked_batch",
                event_id,
            )

        except Exception as e:
            logger.error(
                "Failed to handle videos keyframes masked batch",
                job_id=job_id,
                event_id=event_data.get("event_id"),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
