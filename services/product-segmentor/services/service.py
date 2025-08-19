"""Product Segmentor Service business logic.

This service orchestrates product segmentation operations by delegating to specialized modules:
- SegmentorFactory: Creates and manages segmentation engines
- ProgressTracker: Tracks job progress and asset counts
- CompletionManager: Handles batch completion and watermark emission
- Deduper: Prevents duplicate processing
- ForegroundProcessor: Handles image segmentation operations
- DatabaseUpdater: Manages database operations

The service maintains a stable public API while internal responsibilities are modularized.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Set
from datetime import datetime
import numpy as np
import cv2
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.logging_config import configure_logging

from utils.file_manager import FileManager
from config_loader import config
from handlers.event_emitter import EventEmitter
from .foreground_processor import ForegroundProcessor
from .image_masking_processor import ImageMaskingProcessor
from utils.db_updater import DatabaseUpdater
from .foreground_segmentor_factory import create_segmentor
from segmentation.models.yolo_segmentor import YOLOSegmentor
from utils.completion_manager import CompletionManager
from utils.deduper import Deduper
from .asset_processor import AssetProcessor # New import
from vision_common import JobProgressManager

logger = configure_logging("product-segmentor-service", config.LOG_LEVEL)

class ProductSegmentorService:
    """Core business logic for product segmentation. 
    
    This service orchestrates segmentation operations by delegating to specialized modules:
    - SegmentorFactory: Creates and manages segmentation engines
    - ProgressTracker: Tracks job progress and asset counts
    - CompletionManager: Handles batch completion and watermark emission
    - Deduper: Prevents duplicate processing
    - ForegroundProcessor: Handles image segmentation operations
    - DatabaseUpdater: Manages database operations
    
    The service maintains a stable public API while internal responsibilities are modularized.
    """
    
    def __init__(
        self,
        db: DatabaseManager,
        broker: MessageBroker,
        foreground_model_name: str = config.FOREGROUND_SEG_MODEL_NAME,
        max_concurrent: int = 4
    ):
        """Initialize segmentation service. 
        
        Args:
            db: Database manager instance
            broker: Message broker instance
            model_name: Hugging Face model name
            max_concurrent: Maximum concurrent image processing
            
        Initializes specialized modules:
        - SegmentorFactory: Creates segmentation engines
        - ProgressTracker: Tracks job progress
        - CompletionManager: Handles batch completion
        - Deduper: Prevents duplicate processing
        - ImageProcessor: Handles image segmentation
        - DatabaseUpdater: Manages database operations
        """
        self.db = db
        self.broker = broker
        self.file_manager = FileManager(
            foreground_mask_dir_path=config.FOREGROUND_MASK_DIR_PATH,
            people_mask_dir_path=config.PEOPLE_MASK_DIR_PATH,
            product_mask_dir_path=config.PRODUCT_MASK_DIR_PATH
        )
        self.max_concurrent = max_concurrent
        
        # Initialize segmentation engine using factory
        self.foreground_segmentor = create_segmentor(foreground_model_name, config.HF_TOKEN)
        self.people_segmentor = YOLOSegmentor(config.PEOPLE_SEG_MODEL_NAME)
        
        # Initialize event emitter
        self.event_emitter = EventEmitter(broker)
        
        # Initialize processing helpers
        self.image_processor = ForegroundProcessor(self.foreground_segmentor)
        self.db_updater = DatabaseUpdater(self.db)
        
        # Initialize new modules
        self.job_progress_manager = JobProgressManager(broker)
        self.completion_manager = CompletionManager(self.event_emitter, self.job_progress_manager)
        self.deduper = Deduper()
        
        self.image_masking_processor = ImageMaskingProcessor(
            self.foreground_segmentor,
            self.people_segmentor,
            self.file_manager,
            self.image_processor
        )
        
        self._processing_semaphore = asyncio.Semaphore(int(max_concurrent))
        
        # Initialize AssetProcessor
        self.asset_processor = AssetProcessor(
            deduper=self.deduper,
            image_masking_processor=self.image_masking_processor,
            db_updater=self.db_updater,
            event_emitter=self.event_emitter,
            job_progress_manager=self.job_progress_manager,
            completion_manager=self.completion_manager
        )
        
        self.initialized = False
    
    # Pass-through accessors for backward compatibility - delegate to specialized modules
    @property
    def job_image_counts(self) -> Dict[str, Dict[str, int]]:
        """Get job image counts (delegated to JobProgressManager)."""
        return self.job_progress_manager.job_image_counts
    
    @property
    def job_frame_counts(self) -> Dict[str, Dict[str, int]]:
        """Get job frame counts (delegated to JobProgressManager)."""
        return self.job_progress_manager.job_frame_counts
    
    @property
    def processed_assets(self) -> Set[str]:
        """Get processed assets (delegated to JobProgressManager)."""
        return self.job_progress_manager.processed_assets
    
    @property
    def watermark_timers(self) -> Dict[str, asyncio.Task]:
        """Get watermark timers (delegated to JobProgressManager)."""
        return self.job_progress_manager.watermark_timers.copy()
    
    @property
    def _completion_events_sent(self) -> Set[str]:
        """Get completion events sent (delegated to JobProgressManager)."""
        return self.job_progress_manager._completion_events_sent.copy()
    
    async def initialize(self) -> None:
        """Initialize the service."""
        try:
            logger.info("Initializing Product Segmentor Service")
            
            # Initialize file manager
            await self.file_manager.initialize()
            
            # Initialize segmentation model
            await self.foreground_segmentor.initialize()
            await self.people_segmentor.initialize()
            
            self.initialized = True
            logger.info("Product Segmentor Service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize service", error=str(e))
            raise
    
    async def cleanup(self) -> None:
        """Cleanup service resources."""
        try:
            # Wait for any ongoing processing to complete
            logger.info("Waiting for ongoing processing to complete")
            
            # Acquire all semaphore permits to ensure no new processing starts
            permits_acquired = 0
            try:
                for _ in range(self.max_concurrent):
                    await asyncio.wait_for(self._processing_semaphore.acquire(), timeout=30.0)
                    permits_acquired += 1
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for processing to complete")
            
            # Cleanup segmentation model
            if self.foreground_segmentor:
                self.foreground_segmentor.cleanup()
            if self.people_segmentor:
                self.people_segmentor.cleanup()
            
            # Cleanup progress tracking using new specialized modules
            await self.job_progress_manager.cleanup_all()
            self.completion_manager.cleanup_all()
            self.deduper.clear_all()
            
            # Release acquired permits
            for _ in range(permits_acquired):
                self._processing_semaphore.release()
            
            self.initialized = False
            logger.info("Service cleanup completed")
            
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))
    
    async def handle_products_image_ready(self, event_data: dict) -> None:
        """Handle single product image ready event. 
        
        Args:
            event_data: Event payload containing image information
        """
        await self.asset_processor.handle_single_asset_processing(
            event_data=event_data,
            asset_type="image",
            asset_id_key="image_id",
            db_update_func=self.db_updater.update_product_image_mask,
            emit_masked_func=self.event_emitter.emit_product_image_masked
        )
    
    async def handle_products_images_ready_batch(self, event_data: dict) -> None:
        """Handle product images batch completion event. 
        
        Args:
            event_data: Batch event payload
        """
        try:
            job_id = event_data["job_id"]
            total_images = event_data["total_images"]
            
            logger.info("Batch event received",
                       job_id=job_id,
                       asset_type="image",
                       total_items=total_images,
                       event_type="products_images_ready_batch")
            
            # Store the total image count for the job using job progress manager
            await self.job_progress_manager.update_job_progress(job_id, "image", total_images, 0, "segmentation")
            logger.info("Batch tracking initialized",
                       job_id=job_id,
                       asset_type="image",
                       total_items=total_images)
            
            # Start watermark timer using job progress manager
            await self.job_progress_manager._start_watermark_timer(job_id, 300, "segmentation")
            
            # If there are no images, immediately publish batch completion event
            if total_images == 0:
                logger.info("Immediate completion for zero-asset job", job_id=job_id, asset_type="image")
                # Publish immediate batch completion event for empty batch
                await self.event_emitter.emit_products_images_masked_batch(
                    job_id=job_id,
                    total_images=0
                )
                
        except Exception as e:
            logger.error("Failed to handle products images ready batch", job_id=job_id, error=str(e))
            raise
    
    async def handle_videos_keyframes_ready(self, event_data: dict) -> None:
        """Handle video keyframes ready event. 
        
        Args:
            event_data: Event payload containing keyframe information
        """
        video_id = event_data["video_id"]
        frames = event_data["frames"]
        job_id = event_data["job_id"]

        logger.info("Starting batch processing",
                   job_id=job_id,
                   asset_type="video",
                   total_items=len(frames),
                   operation="segmentation")

        processed_frames = []

        for frame in frames:
            frame_id = frame["frame_id"]
            ts = frame["ts"]
            local_path = frame["local_path"]

            mask_path = await self.asset_processor.handle_single_asset_processing(
                event_data=frame,
                asset_type="frame",
                asset_id_key="frame_id",
                db_update_func=self.db_updater.update_video_frame_mask,
                emit_masked_func=None, # Individual frame masked event is handled by emit_video_keyframes_masked
                job_id=job_id # Pass job_id explicitly for frames
            )

            if mask_path:
                processed_frames.append({
                    "frame_id": frame_id,
                    "ts": ts,
                    "mask_path": mask_path
                })

        if processed_frames:
            await self.event_emitter.emit_video_keyframes_masked(job_id=job_id, video_id=video_id, frames=processed_frames)
            logger.info("Video keyframes processed", video_id=video_id, processed=len(processed_frames))

        # Update progress for the batch of frames (completion check handled by individual processing)  
        await self.job_progress_manager.update_job_progress(job_id, "frame", len(frames), 0, "segmentation")
        
        # Note: Completion check moved to individual asset processing to avoid duplicate events
    
    async def handle_videos_keyframes_ready_batch(self, event_data: dict) -> None:
        """Handle video keyframes batch completion event.

        Args:
            event_data: Batch event payload
        """
        try:
            job_id = event_data["job_id"]
            event_id = event_data.get("event_id", str(uuid.uuid4()))  # Generate if not provided
            total_keyframes = event_data.get("total_keyframes", 0)

            logger.info("Batch event received",
                       job_id=job_id,
                       asset_type="video",
                       total_items=total_keyframes,
                       event_type="videos_keyframes_ready_batch",
                       event_id=event_id)

            # Store the total frame count for the job using job progress manager
            await self.job_progress_manager.update_job_progress(job_id, "frame", total_keyframes, 0, "segmentation")
            logger.info("Batch tracking initialized",
                       job_id=job_id,
                       asset_type="video",
                       total_items=total_keyframes)

            # Start watermark timer using job progress manager
            await self.job_progress_manager._start_watermark_timer(job_id, 300, "segmentation")

            # Emit videos keyframes masked batch event for all cases (both zero and non-zero keyframes)
            await self.event_emitter.emit_videos_keyframes_masked_batch(
                job_id=job_id,
                total_keyframes=total_keyframes
            )
            logger.info("Published videos keyframes masked batch event", job_id=job_id, total_keyframes=total_keyframes)

        except Exception as e:
            logger.error("Failed to handle videos keyframes ready batch", job_id=job_id, event_id=event_id, error=str(e))
            raise
