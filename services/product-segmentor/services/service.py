"""Product Segmentor Service business logic.

This service orchestrates product segmentation operations by delegating to specialized modules:
- SegmentorFactory: Creates and manages segmentation engines
- ProgressTracker: Tracks job progress and asset counts
- CompletionManager: Handles batch completion and watermark emission
- Deduper: Prevents duplicate processing
- ImageProcessor: Handles image segmentation operations
- DatabaseUpdater: Manages database operations

The service maintains a stable public API while internal responsibilities are modularized.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Set
from datetime import datetime
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.logging_config import configure_logging

from utils.file_manager import FileManager
from config_loader import config
from handlers.event_emitter import EventEmitter
from .image_processor import ImageProcessor
from utils.db_updater import DatabaseUpdater
from .segmentor_factory import create_segmentor
from utils.progress_tracker import ProgressTracker
from utils.completion_manager import CompletionManager
from utils.deduper import Deduper

logger = configure_logging("product-segmentor-service", config.LOG_LEVEL)

class ProductSegmentorService:
    """Core business logic for product segmentation.
    
    This service orchestrates segmentation operations by delegating to specialized modules:
    - SegmentorFactory: Creates and manages segmentation engines
    - ProgressTracker: Tracks job progress and asset counts
    - CompletionManager: Handles batch completion and watermark emission
    - Deduper: Prevents duplicate processing
    - ImageProcessor: Handles image segmentation operations
    - DatabaseUpdater: Manages database operations
    
    The service maintains a stable public API while internal responsibilities are modularized.
    """
    
    def __init__(
        self,
        db: DatabaseManager,
        broker: MessageBroker,
        model_name: str = "briaai/RMBG-2.0",
        mask_base_path: str = "data/masks",
        max_concurrent: int = 4
    ):
        """Initialize segmentation service.
        
        Args:
            db: Database manager instance
            broker: Message broker instance
            model_name: Hugging Face model name
            mask_base_path: Base path for mask storage
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
        self.file_manager = FileManager(mask_base_path)
        self.max_concurrent = max_concurrent
        
        # Initialize segmentation engine using factory
        self.segmentor = create_segmentor(model_name, config.HF_TOKEN)
        
        # Initialize event emitter
        self.event_emitter = EventEmitter(broker)
        
        # Initialize processing helpers
        self.image_processor = ImageProcessor(self.segmentor)
        self.db_updater = DatabaseUpdater(self.db)
        
        # Initialize new modules
        self.progress_tracker = ProgressTracker()
        self.completion_manager = CompletionManager(self.event_emitter)
        self.deduper = Deduper()
        
        self._processing_semaphore = asyncio.Semaphore(int(max_concurrent))
        
        # Legacy attributes are now handled by properties that delegate to new modules
        
        self.initialized = False
    
    # Pass-through accessors for backward compatibility - delegate to specialized modules
    @property
    def job_image_counts(self) -> Dict[str, Dict[str, int]]:
        """Get job image counts (delegated to ProgressTracker)."""
        return self.progress_tracker.get_all_job_counts()
    
    @property
    def job_frame_counts(self) -> Dict[str, Dict[str, int]]:
        """Get job frame counts (delegated to ProgressTracker)."""
        return self.progress_tracker.get_all_job_counts()
    
    @property
    def processed_assets(self) -> Set[str]:
        """Get processed assets (delegated to Deduper)."""
        return self.deduper.get_processed_assets()
    
    @property
    def watermark_timers(self) -> Dict[str, asyncio.Task]:
        """Get watermark timers (delegated to CompletionManager)."""
        return self.completion_manager._watermark_timers.copy()
    
    @property
    def _completion_events_sent(self) -> Set[str]:
        """Get completion events sent (delegated to CompletionManager)."""
        return self.completion_manager._completion_events_sent.copy()
    
    async def initialize(self) -> None:
        """Initialize the service."""
        try:
            logger.info("Initializing Product Segmentor Service")
            
            # Initialize file manager
            await self.file_manager.initialize()
            
            # Initialize segmentation model
            await self.segmentor.initialize()
            
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
            if self.segmentor:
                self.segmentor.cleanup()
            
            # Clear batch trackers (legacy - kept for backward compatibility)
            self._batch_trackers.clear()
            
            # Cleanup progress tracking using new specialized modules
            self.completion_manager.cleanup_all()
            self.progress_tracker.clear_all()
            self.deduper.clear_all()
            
            # Release acquired permits
            for _ in range(permits_acquired):
                self._processing_semaphore.release()
            
            self.initialized = False
            logger.info("Service cleanup completed")
            
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))
    
    # Legacy methods removed - functionality moved to specialized modules:
    # - Progress tracking: completion_manager.py and progress_tracker.py
    # - Batch completion: completion_manager.py
    # - Asset deduplication: deduper.py
    
    
    async def handle_products_image_ready(self, event_data: dict) -> None:
        """Handle single product image ready event.
        
        Args:
            event_data: Event payload containing image information
        """
        try:
            product_id = event_data["product_id"]
            image_id = event_data["image_id"]
            local_path = event_data["local_path"]
            job_id = event_data.get("job_id")
            
            # Create a unique key for this asset
            asset_key = f"{job_id}:{image_id}"
            
            # Skip if we've already processed this asset using deduper
            if self.deduper.is_processed(asset_key):
                logger.info("Skipping duplicate asset", image_id=image_id, job_id=job_id)
                return
                
            # Mark as processed using deduper
            self.deduper.mark_processed(asset_key)
            
            logger.info("Processing product image", image_id=image_id, product_id=product_id)
            
            # Process image with concurrency control
            async with self._processing_semaphore:
                mask_path = await self._process_single_image(image_id, local_path, "product")
            
            if mask_path:
                db_update_success = False
                try:
                    # Update database
                    await self._update_product_image_mask(image_id, mask_path)
                    db_update_success = True
                    
                    # Emit masked event
                    await self.event_emitter.emit_product_image_masked(job_id=job_id, image_id=image_id, mask_path=mask_path)
                    
                    logger.info("Product image processed successfully", image_id=image_id)
                    
                    # Update job progress tracking using progress tracker
                    self.progress_tracker.increment_processed(job_id, 'image')
                    all_counts = self.progress_tracker.get_job_counts(job_id)
                    image_counts = all_counts.get('image', {'total': 0, 'processed': 0})
                    current_count = image_counts['processed']
                    total_count = image_counts['total']
                    
                    logger.info("Updated job image counters", job_id=job_id,
                               processed=current_count, total=total_count)
                    
                    # Check if all images are processed
                    if current_count >= total_count:
                        logger.info("All images processed for job", job_id=job_id,
                                   processed=current_count, total=total_count)
                        
                        # Publish completion event using completion manager
                        await self.completion_manager.publish_completion(job_id, self.progress_tracker)
                        
                        # Remove job from tracking
                        self.progress_tracker.remove_job(job_id)
                        logger.info("Removed job from tracking", job_id=job_id)
                        
                except Exception as e:
                    logger.error("Failed to update database or emit event for product image", image_id=image_id, error=str(e))
                    # Don't re-raise, allow processing to continue
                    # Don't update progress or check completion if database update failed
                    if not db_update_success:
                        return
            else:
                logger.warning("Failed to process product image", image_id=image_id)
                
        except Exception as e:
            logger.error("Error processing product image", error=str(e), event_data=event_data)
    
    async def handle_products_images_ready_batch(self, event_data: dict) -> None:
        """Handle product images batch completion event.
        
        Args:
            event_data: Batch event payload
        """
        try:
            job_id = event_data["job_id"]
            total_images = event_data["total_images"]
            
            logger.info("Products images ready batch received", job_id=job_id, total_images=total_images)
            
            # Store the total image count for the job using progress tracker
            self.progress_tracker.update_job_counts(job_id, 'image', total_images, 0)
            logger.info("Initialized job image counters", job_id=job_id, total_images=total_images)    
            
            # Start watermark timer using completion manager
            self.completion_manager.start_timer(job_id)
            
            # If there are no images, immediately publish batch completion event
            if total_images == 0:
                logger.info("No images found for job, publishing immediate batch completion", job_id=job_id)
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
        try:
            video_id = event_data["video_id"]
            frames = event_data["frames"]
            job_id = event_data["job_id"]
            
            logger.info("Processing video keyframes", video_id=video_id, frame_count=len(frames))
            
            processed_frames = []
            
            # Process each frame
            for frame in frames:
                frame_id = frame["frame_id"]
                ts = frame["ts"]
                local_path = frame["local_path"]
                
                # Create a unique key for this asset
                asset_key = f"{job_id}:{frame_id}"
                
                # Skip if we've already processed this asset using deduper
                if self.deduper.is_processed(asset_key):
                    logger.info("Skipping duplicate asset", frame_id=frame_id, job_id=job_id)
                    continue
                    
                # Mark as processed using deduper
                self.deduper.mark_processed(asset_key)
                
                # Process frame with concurrency control
                async with self._processing_semaphore:
                    mask_path = await self._process_single_image(frame_id, local_path, "frame")
                
                if mask_path:
                    db_update_success = False
                    try:
                        # Update database
                        await self._update_video_frame_mask(frame_id, mask_path)
                        db_update_success = True
                        
                        processed_frames.append({
                            "frame_id": frame_id,
                            "ts": ts,
                            "mask_path": mask_path
                        })
                        
                        # Update job progress tracking using progress tracker
                        self.progress_tracker.increment_processed(job_id, 'frame')
                        all_counts = self.progress_tracker.get_job_counts(job_id)
                        frame_counts = all_counts.get('frame', {'total': 0, 'processed': 0})
                        current_count = frame_counts['processed']
                        total_count = frame_counts['total']
                        
                        logger.info("Updated job frame counters", job_id=job_id,
                                   processed=current_count, total=total_count)
                        
                        # Check if all frames are processed
                        if current_count >= total_count:
                            logger.info("All frames processed for job", job_id=job_id,
                                       processed=current_count, total=total_count)
                            
                            # Publish completion event using completion manager
                            await self.completion_manager.publish_completion(job_id, self.progress_tracker)
                            
                            # Remove job from tracking
                            self.progress_tracker.remove_job(job_id)
                            logger.info("Removed job from tracking", job_id=job_id)
                            
                    except Exception as e:
                        logger.error("Failed to update database for video frame", frame_id=frame_id, error=str(e))
                        # Don't re-raise, allow processing to continue
                        # Don't update progress or check completion if database update failed
                        if not db_update_success:
                            continue
                else:
                    logger.warning("Failed to process frame", frame_id=frame_id)
                    continue  # Skip this frame if processing failed
            
            # Emit masked event if any frames were processed
            if processed_frames:
                await self.event_emitter.emit_video_keyframes_masked(job_id=job_id, video_id=video_id, frames=processed_frames)
                logger.info("Video keyframes processed", video_id=video_id, processed=len(processed_frames))
            
        except Exception as e:
            logger.error("Error processing video keyframes", error=str(e), event_data=event_data)
    
    async def handle_videos_keyframes_ready_batch(self, event_data: dict) -> None:
        """Handle video keyframes batch completion event.

        Args:
            event_data: Batch event payload
        """
        try:
            job_id = event_data["job_id"]
            event_id = event_data.get("event_id", str(uuid.uuid4()))  # Generate if not provided
            total_keyframes = event_data.get("total_keyframes", 0)

            logger.info("Videos keyframes ready batch received", job_id=job_id, event_id=event_id, total_keyframes=total_keyframes)

            # Store the total frame count for the job using progress tracker
            self.progress_tracker.update_job_counts(job_id, 'frame', total_keyframes, 0)
            logger.info("Initialized job frame counters", job_id=job_id, total_frames=total_keyframes)

            # Start watermark timer using completion manager
            self.completion_manager.start_timer(job_id)

            # If there are no keyframes, immediately publish batch completion event
            if total_keyframes == 0:
                logger.info("No keyframes found for job, publishing immediate batch completion", job_id=job_id)
                # Publish immediate batch completion event for empty batch
                await self.event_emitter.emit_videos_keyframes_masked_batch(
                    job_id=job_id,
                    total_keyframes=0
                )

        except Exception as e:
            logger.error("Failed to handle videos keyframes ready batch", job_id=job_id, event_id=event_id, error=str(e))
            raise
    
    async def _process_single_image(self, image_id: str, local_path: str, image_type: str) -> Optional[str]:
        """Process a single image to generate mask.
        
        Args:
            image_id: Unique identifier for the image
            local_path: Path to the source image
            image_type: Type of image ("product" or "frame")
            
        Returns:
            Path to generated mask or None if processing failed
        """
        try:
            return await self.image_processor.process_image(
                image_id=image_id,
                local_path=local_path,
                image_type=image_type,
                file_manager=self.file_manager,
            )
        except Exception as e:
            logger.error("Error processing image", image_id=image_id, error=str(e))
            return None
    
    async def _update_product_image_mask(self, image_id: str, mask_path: str) -> None:
        """Update product image record with mask path."""
        try:
            await self.db_updater.update_product_image_mask(image_id, mask_path)
        except Exception as e:
            logger.error("Failed to update product image mask", image_id=image_id, error=str(e))
    
    async def _update_video_frame_mask(self, frame_id: str, mask_path: str) -> None:
        """Update video frame record with mask path."""
        try:
            await self.db_updater.update_video_frame_mask(frame_id, mask_path)
        except Exception as e:
            logger.error("Failed to update video frame mask", frame_id=frame_id, error=str(e))
    
    async def _publish_completion_event(self, job_id: str) -> None:
        """Publish completion event for a job.
        
        Args:
            job_id: Job identifier
        """
        try:
            # Check if completion event already sent for this job
            if job_id in self._completion_events_sent:
                logger.debug("Completion event already sent for job", job_id=job_id)
                return
            
            # Get job progress
            all_counts = self.progress_tracker.get_job_counts(job_id)
            image_counts = all_counts.get('image', {'total': 0, 'processed': 0})
            frame_counts = all_counts.get('frame', {'total': 0, 'processed': 0})
            
            # Check if all assets processed
            images_complete = (image_counts['total'] > 0 and
                             image_counts['processed'] >= image_counts['total'])
            frames_complete = (frame_counts['total'] > 0 and
                              frame_counts['processed'] >= frame_counts['total'])
            
            # If both types are complete (or have no assets), publish completion
            if images_complete and frames_complete:
                logger.info("Publishing completion event for job", job_id=job_id)
                
                # Publish completion event
                completion_event = {
                    "job_id": job_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "completed"
                }
                
                await self.broker.publish_event(
                    event_type="products.images.masked.completed",
                    payload=completion_event
                )
                
                self._completion_events_sent.add(job_id)
                logger.info("Completion event published successfully", job_id=job_id)
            else:
                logger.debug("Job not ready for completion",
                           job_id=job_id,
                           images_complete=images_complete,
                           frames_complete=frames_complete)
                
        except Exception as e:
            logger.error("Failed to publish completion event",
                        job_id=job_id, error=str(e))
    