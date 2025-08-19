from common_py.logging_config import configure_logging
from typing import Dict, Any, List, Optional
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import ProductImageCRUD, VideoFrameCRUD
from embedding import EmbeddingExtractor
import uuid
import asyncio
from vision_common import JobProgressManager

logger = configure_logging("vision-embedding")


class VisionEmbeddingService:
    """Main service class for vision embedding with progress tracking"""
    
    def __init__(self, db: DatabaseManager, broker: MessageBroker, embed_model: str):
        self.db = db
        self.broker = broker
        self.image_crud = ProductImageCRUD(db)
        self.frame_crud = VideoFrameCRUD(db)
        logger.info("Initializing vision embedding service", model_name=embed_model)
        self.extractor = EmbeddingExtractor(embed_model)
        self.progress_manager = JobProgressManager(broker)
    
    async def initialize(self):
        """Initialize the embedding extractor"""
        await self.extractor.initialize()
    
    async def cleanup(self):
        """Clean up resources"""
        await self.extractor.cleanup()
        await self.progress_manager.cleanup_all()
    
    # Helper methods for common patterns
    async def _publish_embedding_ready_event(self, asset_type: str, job_id: str, asset_id: str):
        """Publish embedding ready event for a single asset"""
        event_id = str(uuid.uuid4())
        await self.broker.publish_event(
            f"{asset_type}.embedding.ready",
            {
                "job_id": job_id,
                "asset_id": asset_id,
                "event_id": event_id
            }
        )
    
    async def _handle_batch_initialization(self, job_id: str, asset_type: str, total_items: int, event_type: str, event_id: str = None):
        """Common batch initialization logic"""
        logger.info("Batch event received",
                   job_id=job_id,
                   asset_type=asset_type,
                   total_items=total_items,
                   event_type=event_type)
        
        # Store the total count for the job
        if asset_type == "image":
            self.progress_manager.job_image_counts[job_id] = {'total': total_items, 'processed': 0}
        else:  # video
            self.progress_manager.expected_total_frames[job_id] = total_items
            self.progress_manager.job_frame_counts[job_id] = {'total': total_items, 'processed': 0}
        
        logger.info("Batch tracking initialized",
                   job_id=job_id,
                   asset_type=asset_type,
                   total_items=total_items)
        
        # Mark batch as initialized
        self.progress_manager._mark_batch_initialized(job_id, asset_type)
        
        # If there are no items, immediately publish completion event
        if total_items == 0:
            logger.info("Immediate completion for zero-asset job", job_id=job_id, asset_type=asset_type)
            await self.progress_manager.publish_completion_event_with_count(job_id, asset_type, 0, 0, "embeddings")
    
    async def _handle_single_asset_processing(self, job_id: str, asset_id: str, asset_type: str, local_path: str,
                                            crud, extract_func, is_masked: bool = False, mask_path: str = None):
        """Common single asset processing logic"""
        # Create a unique key for this asset
        asset_key = f"{job_id}:{asset_id}"
        
        # Skip if we've already processed this asset
        if asset_key in self.progress_manager.processed_assets:
            logger.info("Skipping duplicate asset", job_id=job_id, asset_id=asset_id, asset_type=asset_type)
            return False
            
        # Add to processed assets
        self.progress_manager.processed_assets.add(asset_key)
        
        logger.info("Processing item",
                   job_id=job_id,
                   asset_id=asset_id,
                   asset_type=asset_type,
                   item_path=local_path,
                   operation="masked_processing" if is_masked else "normal_processing")
        
        # Extract embeddings
        if is_masked and mask_path:
            emb_rgb, emb_gray = await extract_func(local_path, mask_path)
        else:
            emb_rgb, emb_gray = await extract_func(local_path)
        
        if emb_rgb is not None and emb_gray is not None:
            # Update database with embeddings
            await crud.update_embeddings(asset_id, emb_rgb.tolist(), emb_gray.tolist())
            
            # Emit embedding ready event
            await self._publish_embedding_ready_event(asset_type, job_id, asset_id)
            
            logger.info("Item processed successfully",
                       job_id=job_id,
                       asset_id=asset_id,
                       asset_type=asset_type)
            return True
        else:
            logger.error("Item processing failed",
                        job_id=job_id,
                        asset_id=asset_id,
                        asset_type=asset_type,
                        error=f"Failed to extract embeddings {'from masked ' + asset_type if is_masked else ''}")
            return False
    
    async def _update_and_check_completion(self, job_id: str, asset_type: str):
        """Update progress and check if batch is complete (batch-first pattern)"""
        # Update job progress tracking only if we have job counts initialized
        job_counts = None
        if asset_type == "image":
            job_counts = self.progress_manager.job_image_counts.get(job_id)
        else:  # video
            job_counts = self.progress_manager.job_frame_counts.get(job_id)
            
        if not job_counts:
            logger.warning("Job counts not initialized for job, skipping completion tracking", job_id=job_id)
            return
            
        # Check if batch has been initialized
        if not self.progress_manager._is_batch_initialized(job_id, asset_type):
            logger.warning("Batch not initialized for job, skipping completion tracking", job_id=job_id)
            return
            
        # Increment processed count
        job_counts['processed'] += 1
        current_count = job_counts['processed']
        total_count = job_counts['total']
        
        logger.debug("Progress update",
                    job_id=job_id,
                    asset_type=asset_type,
                    processed=current_count,
                    total=total_count)
        
        # Check if all items are processed
        if current_count >= total_count:
            logger.info("Batch completed",
                       job_id=job_id,
                       asset_type=asset_type,
                       processed=current_count,
                       total=total_count)
            
            # Publish completion event
            await self.progress_manager.publish_completion_event_with_count(
                job_id, asset_type, total_count, current_count, "embeddings"
            )
            
            # Clean up job tracking
            self.progress_manager._cleanup_job_tracking(job_id)
            logger.info("Removed job from tracking", job_id=job_id)

    async def _update_and_check_completion_per_asset_first(self, job_id: str, asset_type: str):
        """Update progress and check if batch is complete (per-asset first pattern)"""
        # Initialize job tracking with high expected count if not already initialized
        if job_id not in self.progress_manager.job_tracking:
            logger.info("Initializing job tracking with high expected count (per-asset first)", job_id=job_id, asset_type=asset_type)
            await self.progress_manager.initialize_with_high_expected(job_id, asset_type)
        
        # Update job progress tracking
        await self.progress_manager.update_job_progress(job_id, asset_type, 0, increment=1, event_type_prefix="embeddings")
        
        # Check if batch has been initialized (real expected count available)
        if self.progress_manager._is_batch_initialized(job_id, asset_type):
            # Get real expected count from batch tracking
            if asset_type == "image":
                job_counts = self.progress_manager.job_image_counts.get(job_id)
                real_expected = job_counts['total'] if job_counts else 0
            else:  # video
                real_expected = self.progress_manager.expected_total_frames.get(job_id, 0)
            
            if real_expected > 0:
                logger.info("Batch initialized, updating with real expected count", job_id=job_id, asset_type=asset_type, real_expected=real_expected)
                
                # Update expected count with real value and re-check completion
                is_complete = await self.progress_manager.update_expected_and_recheck_completion(job_id, asset_type, real_expected, "embeddings")
                
                if is_complete:
                    # Get current done count for completion event
                    job_data = self.progress_manager.job_tracking[job_id]
                    done_count = job_data["done"]
                    
                    # Publish completion event
                    await self.progress_manager.publish_completion_event_with_count(
                        job_id, asset_type, real_expected, done_count, "embeddings"
                    )
                    
                    # Clean up job tracking
                    self.progress_manager._cleanup_job_tracking(job_id)
                    logger.info("Removed job from tracking after per-asset first completion", job_id=job_id)
    
    async def handle_products_images_ready_batch(self, event_data: Dict[str, Any]):
        """Handle products images ready batch event to initialize job tracking"""
        try:
            job_id = event_data["job_id"]
            total_images = event_data["total_images"]
            
            await self._handle_batch_initialization(job_id, "image", total_images, "products_images_ready_batch")
            
        except Exception as e:
            logger.error("Failed to handle products images ready batch",
                        job_id=job_id,
                        error=str(e),
                        error_type=type(e).__name__)
            raise
    
    async def handle_videos_keyframes_ready_batch(self, event_data: Dict[str, Any]):
        """Handle videos keyframes ready batch event to initialize job tracking"""
        try:
            job_id = event_data["job_id"]
            event_id = event_data["event_id"]
            total_keyframes = event_data["total_keyframes"]
            
            # Create a unique identifier for this batch event to detect duplicates
            batch_event_key = f"{job_id}:{event_id}"
            
            # Check if we've already processed this batch event
            if batch_event_key in self.progress_manager.processed_batch_events:
                logger.info("Ignoring duplicate batch event", job_id=job_id, event_id=event_id, asset_type="video")
                return
            
            # Mark this batch event as processed
            self.progress_manager.processed_batch_events.add(batch_event_key)
            
            await self._handle_batch_initialization(job_id, "video", total_keyframes, "videos_keyframes_ready_batch", event_id)
            
        except Exception as e:
            logger.error("Failed to handle videos keyframes ready batch",
                        job_id=job_id,
                        event_id=event_data.get("event_id"),
                        error=str(e),
                        error_type=type(e).__name__)
            raise
    
    async def handle_products_images_masked_batch(self, event_data: Dict[str, Any]):
        """Handle products images masked batch event to initialize job tracking"""
        try:
            job_id = event_data["job_id"]
            total_images = event_data["total_images"]
            
            await self._handle_batch_initialization(job_id, "image", total_images, "products_images_masked_batch")
            
        except Exception as e:
            logger.error("Failed to handle products images masked batch",
                        job_id=job_id,
                        error=str(e),
                        error_type=type(e).__name__)
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
                logger.info("Ignoring duplicate batch event", job_id=job_id, event_id=event_id, asset_type="video")
                return
            
            # Mark this batch event as processed
            self.progress_manager.processed_batch_events.add(batch_event_key)
            
            await self._handle_batch_initialization(job_id, "video", total_keyframes, "videos_keyframes_masked_batch", event_id)
            
        except Exception as e:
            logger.error("Failed to handle videos keyframes masked batch",
                        job_id=job_id,
                        event_id=event_data.get("event_id"),
                        error=str(e),
                        error_type=type(e).__name__)
            raise
    
    async def handle_products_image_ready(self, event_data: Dict[str, Any]):
        """Handle product images ready event"""
        try:
            product_id = event_data["product_id"]
            image_id = event_data["image_id"]
            local_path = event_data["local_path"]
            job_id = event_data.get("job_id")
            
            # Process the single asset
            success = await self._handle_single_asset_processing(
                job_id, image_id, "image", local_path,
                self.image_crud, self.extractor.extract_embeddings
            )
            
            if success:
                # Update progress and check for completion
                await self._update_and_check_completion_per_asset_first(job_id, "image")
                
        except Exception as e:
            logger.error("Item processing failed",
                        job_id=job_id,
                        asset_id=image_id,
                        asset_type="image",
                        error=str(e),
                        error_type=type(e).__name__)
            raise
    
    async def handle_videos_keyframes_ready(self, event_data: Dict[str, Any]):
        """Handle video keyframes ready event"""
        try:
            video_id = event_data["video_id"]
            frames = event_data["frames"]
            job_id = event_data["job_id"]  # job_id is now required
            
            # Process each frame using per-asset first pattern
            for frame_data in frames:
                frame_id = frame_data["frame_id"]
                local_path = frame_data["local_path"]
                
                # Process the single asset
                success = await self._handle_single_asset_processing(
                    job_id, frame_id, "video", local_path,
                    self.frame_crud, self.extractor.extract_embeddings
                )
                
                if success:
                    # Update progress and check for completion (per-asset first pattern)
                    await self._update_and_check_completion_per_asset_first(job_id, "video")
        
        except Exception as e:
            logger.error("Batch processing failed",
                        job_id=job_id,
                        asset_type="video",
                        error=str(e),
                        error_type=type(e).__name__)
            raise
    
    async def handle_products_image_masked(self, event_data: Dict[str, Any]):
        """Handle product image masked event"""
        try:
            job_id = event_data["job_id"]
            image_id = event_data["image_id"]
            mask_path = event_data["mask_path"]
            
            # Get the original image path from database
            image_record = await self.image_crud.get_product_image(image_id)
            if not image_record:
                logger.error("Resource not found",
                            job_id=job_id,
                            asset_id=image_id,
                            asset_type="image",
                            resource_type="image_record")
                return
            
            local_path = image_record.local_path
            
            # Process the single asset with mask
            success = await self._handle_single_asset_processing(
                job_id, image_id, "image", local_path,
                self.image_crud, self.extractor.extract_embeddings_with_mask,
                is_masked=True, mask_path=mask_path
            )
            
            if success:
                # Update progress and check for completion (per-asset first pattern)
                await self._update_and_check_completion_per_asset_first(job_id, "image")
                
        except Exception as e:
            logger.error("Item processing failed",
                        job_id=job_id,
                        asset_id=image_id,
                        asset_type="image",
                        error=str(e),
                        error_type=type(e).__name__)
            raise

    async def handle_video_keyframes_masked(self, event_data: Dict[str, Any]):
        """Handle video keyframes masked event"""
        try:
            job_id = event_data["job_id"]
            video_id = event_data["video_id"]
            frames = event_data["frames"]
            
            # Process each frame using per-asset first pattern
            for frame_data in frames:
                frame_id = frame_data["frame_id"]
                mask_path = frame_data["mask_path"]
                
                # Get the original frame path from database
                frame_record = await self.frame_crud.get_video_frame(frame_id)
                if not frame_record:
                    logger.error("Resource not found",
                                job_id=job_id,
                                asset_id=frame_id,
                                asset_type="video",
                                resource_type="frame_record")
                    continue
                
                local_path = frame_record.local_path
                
                # Process the single asset with mask
                success = await self._handle_single_asset_processing(
                    job_id, frame_id, "video", local_path,
                    self.frame_crud, self.extractor.extract_embeddings_with_mask,
                    is_masked=True, mask_path=mask_path
                )
                
                if success:
                    # Update progress and check for completion (per-asset first pattern)
                    await self._update_and_check_completion_per_asset_first(job_id, "video")
        
        except Exception as e:
            logger.error("Batch processing failed",
                        job_id=job_id,
                        asset_type="video",
                        error=str(e),
                        error_type=type(e).__name__)
            raise
