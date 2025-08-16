"""Product Segmentor Service business logic."""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Set
from datetime import datetime
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.logging_config import configure_logging

from segmentation.interface import SegmentationInterface
from segmentation.rmbg_segmentor import RMBGSegmentor
from file_manager import FileManager
from config_loader import config
from handlers.event_emitter import EventEmitter
from utils.batch_tracker import BatchTracker
from .image_processor import ImageProcessor
from .db_updater import DatabaseUpdater

logger = configure_logging("product-segmentor-service", config.LOG_LEVEL)

class ProductSegmentorService:
    """Core business logic for product segmentation."""
    
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
            model_cache: Model cache directory
            max_concurrent: Maximum concurrent image processing
        """
        self.db = db
        self.broker = broker
        self.file_manager = FileManager(mask_base_path)
        self.max_concurrent = max_concurrent
        
        # Initialize segmentation engine
        self.segmentor = self._create_segmentor(model_name)
        
        # Initialize event emitter
        self.event_emitter = EventEmitter(broker)
        
        # Initialize processing helpers
        self.image_processor = ImageProcessor(self.segmentor, logger)
        self.db_updater = DatabaseUpdater(self.db, logger)
        
        # Batch tracking
        self._batch_trackers: Dict[str, BatchTracker] = {}
        self._processing_semaphore = asyncio.Semaphore(int(max_concurrent))
        
        # Progress tracking
        self.job_image_counts: Dict[str, Dict[str, int]] = {}
        self.job_frame_counts: Dict[str, Dict[str, int]] = {}
        self.processed_assets: Set[str] = set()
        self.watermark_timers: Dict[str, asyncio.Task] = {}
        self._completion_events_sent: Set[str] = set()
        
        self.initialized = False
    
    def _create_segmentor(self, model_name: str) -> SegmentationInterface:
        """Create segmentation engine based on model name."""
        # For now, we only support RMBG models
        # In the future, we can detect model type from model_name or add a separate parameter
        return RMBGSegmentor(model_name=model_name)
    
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
            
            # Clear batch trackers
            self._batch_trackers.clear()
            
            # Cleanup progress tracking
            for timer in self.watermark_timers.values():
                timer.cancel()
            self.watermark_timers.clear()
            self.job_image_counts.clear()
            self.job_frame_counts.clear()
            self.processed_assets.clear()
            self._completion_events_sent.clear()
            
            # Release acquired permits
            for _ in range(permits_acquired):
                self._processing_semaphore.release()
            
            self.initialized = False
            logger.info("Service cleanup completed")
            
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))
    
    async def _start_watermark_timer(self, job_id: str, ttl: int = 300):
        """Start a watermark timer for a job"""
        if job_id in self.watermark_timers:
            self.watermark_timers[job_id].cancel()
        
        async def timer_task():
            await asyncio.sleep(ttl)
            await self._publish_completion_event(job_id, is_timeout=True)
            if job_id in self.watermark_timers:
                del self.watermark_timers[job_id]
        
        self.watermark_timers[job_id] = asyncio.create_task(timer_task())
    
    async def _publish_completion_event(self, job_id: str, is_timeout: bool = False):
        """Publish completion event with timeout handling"""
        logger.info("Starting completion event emission", job_id=job_id, is_timeout=is_timeout)
        
        # For timeout, we need to determine asset type and get counts
        asset_type = "image" if job_id in self.job_image_counts else "video"
        expected = self.job_image_counts.get(job_id, {}).get('total', 0) or self.job_frame_counts.get(job_id, {}).get('total', 0)
        done = self.job_image_counts.get(job_id, {}).get('processed', 0) or self.job_frame_counts.get(job_id, {}).get('processed', 0)
        
        logger.info("Job progress details", job_id=job_id, asset_type=asset_type, expected=expected, done=done)
        
        # Handle zero assets scenario
        if expected == 0:
            done = 0
            logger.info("Immediate completion for zero-asset job", job_id=job_id)
            has_partial = False  # For zero assets, there's no partial completion
        else:
            # Calculate partial completion flag
            has_partial = (done < expected) or is_timeout
            logger.info("Partial completion calculation", job_id=job_id, has_partial=has_partial, done_less_than_expected=done < expected)
        
        # Prepare event data with idempotent flag to prevent duplicate completions
        event_id = str(uuid.uuid4())
        event_data = {
            "job_id": job_id,
            "event_id": event_id,
            "total_assets": expected,
            "processed_assets": done,
            "failed_assets": 0,  # Placeholder - actual failure tracking would be added separately
            "has_partial_completion": has_partial,
            "watermark_ttl": 300,
            "idempotent": True  # Flag to prevent duplicate completions
        }
        
        # Check if this job has already emitted a completion event for this specific asset_type
        completion_key = f"{job_id}:{asset_type}"
        if hasattr(self, '_completion_events_sent') and completion_key in self._completion_events_sent:
            logger.warning("Completion event already sent for this job and asset type, skipping duplicate",
                          job_id=job_id, asset_type=asset_type, completion_key=completion_key)
            return
             
        # Mark this job and asset_type as having sent completion event
        if not hasattr(self, '_completion_events_sent'):
            self._completion_events_sent = set()
        self._completion_events_sent.add(completion_key)
        
        logger.info("Publishing completion event", job_id=job_id, asset_type=asset_type)
        
        try:
            if asset_type == "image":
                await self.event_emitter.emit_products_images_masked_completed(
                    job_id=job_id,
                    total_assets=expected,
                    processed_assets=done,
                    has_partial_completion=has_partial
                )
            else:  # video
                await self.event_emitter.emit_video_keyframes_masked_completed(
                    job_id=job_id,
                    total_assets=expected,
                    processed_assets=done,
                    has_partial_completion=has_partial
                )
        except Exception as e:
            logger.error("Failed to publish completion event via event emitter",
                        job_id=job_id, error=str(e), expected=expected, done=done)
            raise
        
        # Cleanup job tracking
        if job_id in self.job_image_counts:
            logger.info("Cleaning up job image counts", job_id=job_id, remaining_counts=self.job_image_counts[job_id])
            del self.job_image_counts[job_id]
        if job_id in self.job_frame_counts:
            logger.info("Cleaning up job frame counts", job_id=job_id, remaining_counts=self.job_frame_counts[job_id])
            del self.job_frame_counts[job_id]
        if job_id in self.watermark_timers:
            logger.info("Cancelling watermark timer", job_id=job_id)
            self.watermark_timers[job_id].cancel()
            del self.watermark_timers[job_id]
        
        logger.info("Completion event emission completed successfully", job_id=job_id)
    
    
    async def handle_products_images_ready(self, event_data: dict) -> None:
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
            
            # Skip if we've already processed this asset
            if asset_key in self.processed_assets:
                logger.info("Skipping duplicate asset", image_id=image_id, job_id=job_id)
                return
                
            # Add to processed assets
            self.processed_assets.add(asset_key)
            
            logger.info("Processing product image", image_id=image_id, product_id=product_id)
            
            # Process image with concurrency control
            async with self._processing_semaphore:
                mask_path = await self._process_single_image(image_id, local_path, "product")
            
            if mask_path:
                # Update database
                await self._update_product_image_mask(image_id, mask_path)
                
                # Emit masked event
                await self.event_emitter.emit_product_image_masked(job_id, image_id, mask_path)
                
                logger.info("Product image processed successfully", image_id=image_id)
                
                # Update job progress tracking only if we have job counts initialized
                job_counts = self.job_image_counts.get(job_id)
                if job_counts:
                    self.job_image_counts[job_id]['processed'] += 1
                    current_count = self.job_image_counts[job_id]['processed']
                    total_count = self.job_image_counts[job_id]['total']
                    
                    logger.info("Updated job image counters", job_id=job_id,
                               processed=current_count, total=total_count)
                    
                    # Check if all images are processed
                    if current_count >= total_count:
                        logger.info("All images processed for job", job_id=job_id,
                                   processed=current_count, total=total_count)
                        
                        # Publish completion event
                        await self._publish_completion_event(job_id)
                        
                        # Remove job from tracking
                        del self.job_image_counts[job_id]
                        logger.info("Removed job from tracking", job_id=job_id)
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
            
            # Store the total image count for the job
            self.job_image_counts[job_id] = {'total': total_images, 'processed': 0}
            logger.info("Initialized job image counters", job_id=job_id, total_images=total_images)
            
            # Start watermark timer on first asset
            await self._start_watermark_timer(job_id)
            
            # If there are no images, immediately publish completion event
            if total_images == 0:
                logger.info("No images found for job, publishing immediate completion", job_id=job_id)
                await self._publish_completion_event(job_id)
                
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
                
                # Skip if we've already processed this asset
                if asset_key in self.processed_assets:
                    logger.info("Skipping duplicate asset", frame_id=frame_id, job_id=job_id)
                    continue
                    
                # Add to processed assets
                self.processed_assets.add(asset_key)
                
                # Process frame with concurrency control
                async with self._processing_semaphore:
                    mask_path = await self._process_single_image(frame_id, local_path, "frame")
                
                if mask_path:
                    # Update database
                    await self._update_video_frame_mask(frame_id, mask_path)
                    
                    processed_frames.append({
                        "frame_id": frame_id,
                        "ts": ts,
                        "mask_path": mask_path
                    })
                    
                    # logger.info("Frame processed successfully", frame_id=frame_id)
                    
                    # Update job progress tracking only if we have job counts initialized
                    job_counts = self.job_frame_counts.get(job_id)
                    if job_counts:
                        self.job_frame_counts[job_id]['processed'] += 1
                        current_count = self.job_frame_counts[job_id]['processed']
                        total_count = self.job_frame_counts[job_id]['total']
                        
                        logger.info("Updated job frame counters", job_id=job_id,
                                   processed=current_count, total=total_count)
                        
                        # Check if all frames are processed
                        if current_count >= total_count:
                            logger.info("All frames processed for job", job_id=job_id,
                                       processed=current_count, total=total_count)
                            
                            # Publish completion event
                            await self._publish_completion_event(job_id)
                            
                            # Remove job from tracking
                            del self.job_frame_counts[job_id]
                            logger.info("Removed job from tracking", job_id=job_id)
                else:
                    logger.warning("Failed to process frame", frame_id=frame_id)
            
            # Emit masked event if any frames were processed
            if processed_frames:
                await self.event_emitter.emit_video_keyframes_masked(job_id, video_id, processed_frames)
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

            # Store the total frame count for the job
            self.job_frame_counts[job_id] = {'total': total_keyframes, 'processed': 0}
            logger.info("Initialized job frame counters", job_id=job_id, total_frames=total_keyframes)

            # Start watermark timer on first asset
            await self._start_watermark_timer(job_id)

            # If there are no keyframes, immediately publish completion event
            if total_keyframes == 0:
                logger.info("No keyframes found for job, publishing immediate completion", job_id=job_id)
                await self._publish_completion_event(job_id)

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
    