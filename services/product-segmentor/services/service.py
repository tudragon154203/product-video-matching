"""Product Segmentor Service business logic."""

import asyncio
import uuid
from typing import Dict, List, Optional, Set
from datetime import datetime
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.logging_config import configure_logging

from segmentation.interface import SegmentationInterface
from segmentation.rmbg_segmentor import RMBGSegmentor
from file_manager import FileManager

logger = configure_logging("product-segmentor-service")


class ProductSegmentorService:
    """Core business logic for product segmentation."""
    
    def __init__(
        self, 
        db: DatabaseManager, 
        broker: MessageBroker, 
        segmentation_model: str = "rmbg",
        model_name: str = "briaai/RMBG-1.4",
        mask_base_path: str = "data/masks",
        model_cache: Optional[str] = None,
        max_concurrent: int = 4
    ):
        """Initialize segmentation service.
        
        Args:
            db: Database manager instance
            broker: Message broker instance
            segmentation_model: Type of segmentation model to use
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
        self.segmentor = self._create_segmentor(segmentation_model, model_name, model_cache)
        
        # Batch tracking
        self._batch_trackers: Dict[str, BatchTracker] = {}
        self._processing_semaphore = asyncio.Semaphore(max_concurrent)
        
        self.initialized = False
    
    def _create_segmentor(self, model_type: str, model_name: str, cache_dir: Optional[str]) -> SegmentationInterface:
        """Create segmentation engine based on configuration."""
        if model_type.lower() == "rmbg":
            return RMBGSegmentor(model_name=model_name, cache_dir=cache_dir)
        else:
            raise ValueError(f"Unsupported segmentation model: {model_type}")
    
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
            
            # Release acquired permits
            for _ in range(permits_acquired):
                self._processing_semaphore.release()
            
            self.initialized = False
            logger.info("Service cleanup completed")
            
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))
    
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
            
            logger.info("Processing product image", image_id=image_id, product_id=product_id)
            
            # Process image with concurrency control
            async with self._processing_semaphore:
                mask_path = await self._process_single_image(image_id, local_path, "product")
            
            if mask_path:
                # Update database
                await self._update_product_image_mask(image_id, mask_path)
                
                # Emit masked event
                await self._emit_product_image_masked(job_id, image_id, mask_path)
                
                logger.info("Product image processed successfully", image_id=image_id)
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
            
            logger.info("Processing product images batch", job_id=job_id, total_images=total_images)
            
            # Handle edge case: empty batch
            if total_images == 0:
                await self._emit_products_images_masked_batch(job_id, 0)
                logger.info("Empty product images batch processed", job_id=job_id)
                return
            
            # Create or update batch tracker
            if job_id not in self._batch_trackers:
                self._batch_trackers[job_id] = BatchTracker(job_id, "products", total_images)
            
            # Check if batch is already complete
            tracker = self._batch_trackers[job_id]
            if tracker.is_complete():
                await self._emit_products_images_masked_batch(job_id, tracker.processed_count)
                del self._batch_trackers[job_id]
                logger.info("Product images batch completed", job_id=job_id)
                
        except Exception as e:
            logger.error("Error processing product images batch", error=str(e), event_data=event_data)
    
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
                    
                    logger.debug("Frame processed successfully", frame_id=frame_id)
                else:
                    logger.warning("Failed to process frame", frame_id=frame_id)
            
            # Emit masked event if any frames were processed
            if processed_frames:
                await self._emit_video_keyframes_masked(job_id, video_id, processed_frames)
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
            total_keyframes = event_data.get("total_keyframes", 0)
            
            logger.info("Processing video keyframes batch", job_id=job_id, total_keyframes=total_keyframes)
            
            # Handle edge case: empty batch
            if total_keyframes == 0:
                await self._emit_videos_keyframes_masked_batch(job_id, 0)
                logger.info("Empty video keyframes batch processed", job_id=job_id)
                return
            
            # Create or update batch tracker
            batch_key = f"{job_id}_keyframes"
            if batch_key not in self._batch_trackers:
                self._batch_trackers[batch_key] = BatchTracker(job_id, "keyframes", total_keyframes)
            
            # Check if batch is already complete
            tracker = self._batch_trackers[batch_key]
            if tracker.is_complete():
                await self._emit_videos_keyframes_masked_batch(job_id, tracker.processed_count)
                del self._batch_trackers[batch_key]
                logger.info("Video keyframes batch completed", job_id=job_id)
                
        except Exception as e:
            logger.error("Error processing video keyframes batch", error=str(e), event_data=event_data)
    
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
            # Generate mask using segmentation model
            mask = await self.segmentor.segment_image(local_path)
            
            if mask is None:
                logger.warning("Segmentation failed", image_id=image_id, path=local_path)
                return None
            
            # Save mask to filesystem
            if image_type == "product":
                mask_path = await self.file_manager.save_product_mask(image_id, mask)
            else:  # frame
                mask_path = await self.file_manager.save_frame_mask(image_id, mask)
            
            return mask_path
            
        except Exception as e:
            logger.error("Error processing image", image_id=image_id, error=str(e))
            return None
    
    async def _update_product_image_mask(self, image_id: str, mask_path: str) -> None:
        """Update product image record with mask path."""
        try:
            query = """
                UPDATE product_images 
                SET masked_local_path = $1 
                WHERE img_id = $2
            """
            await self.db.execute(query, mask_path, image_id)
            
        except Exception as e:
            logger.error("Failed to update product image mask", image_id=image_id, error=str(e))
    
    async def _update_video_frame_mask(self, frame_id: str, mask_path: str) -> None:
        """Update video frame record with mask path."""
        try:
            query = """
                UPDATE video_frames 
                SET masked_local_path = $1 
                WHERE frame_id = $2
            """
            await self.db.execute(query, mask_path, frame_id)
            
        except Exception as e:
            logger.error("Failed to update video frame mask", frame_id=frame_id, error=str(e))
    
    async def _emit_product_image_masked(self, job_id: str, image_id: str, mask_path: str) -> None:
        """Emit product image masked event."""
        event_data = {
            "event_id": str(uuid.uuid4()),
            "job_id": job_id,
            "image_id": image_id,
            "mask_path": mask_path
        }
        
        await self.broker.publish_event("products.image.masked", event_data)
    
    async def _emit_products_images_masked_batch(self, job_id: str, total_images: int) -> None:
        """Emit products images masked batch event."""
        event_data = {
            "event_id": str(uuid.uuid4()),
            "job_id": job_id,
            "total_images": total_images
        }
        
        await self.broker.publish_event("products.images.masked.batch", event_data)
    
    async def _emit_video_keyframes_masked(self, job_id: str, video_id: str, frames: List[dict]) -> None:
        """Emit video keyframes masked event."""
        event_data = {
            "event_id": str(uuid.uuid4()),
            "job_id": job_id,
            "video_id": video_id,
            "frames": frames
        }
        
        await self.broker.publish_event("video.keyframes.masked", event_data)
    
    async def _emit_videos_keyframes_masked_batch(self, job_id: str, total_keyframes: int) -> None:
        """Emit videos keyframes masked batch event."""
        event_data = {
            "event_id": str(uuid.uuid4()),
            "job_id": job_id,
            "total_keyframes": total_keyframes
        }
        
        await self.broker.publish_event("video.keyframes.masked.batch", event_data)


class BatchTracker:
    """Tracks batch processing completion."""
    
    def __init__(self, job_id: str, batch_type: str, total_count: int):
        """Initialize batch tracker.
        
        Args:
            job_id: Job identifier
            batch_type: Type of batch ("products" or "keyframes")
            total_count: Total number of items in batch
        """
        self.job_id = job_id
        self.batch_type = batch_type
        self.total_count = total_count
        self.processed_count = 0
        self.created_at = datetime.utcnow()
    
    def increment_processed(self) -> None:
        """Increment processed count."""
        self.processed_count += 1
    
    def is_complete(self) -> bool:
        """Check if batch processing is complete."""
        return self.processed_count >= self.total_count