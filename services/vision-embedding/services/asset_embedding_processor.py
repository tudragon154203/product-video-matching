from common_py.logging_config import configure_logging
from typing import Dict, Any, List, Optional
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import ProductImageCRUD, VideoFrameCRUD
from embedding import EmbeddingExtractor
import uuid
import asyncio
from vision_common import JobProgressManager

logger = configure_logging("vision-embedding.services")

class AssetEmbeddingProcessor:
    def __init__(self, extractor: EmbeddingExtractor, image_crud: ProductImageCRUD, frame_crud: VideoFrameCRUD, broker: MessageBroker, progress_manager: JobProgressManager):
        self.extractor = extractor
        self.image_crud = image_crud
        self.frame_crud = frame_crud
        self.broker = broker
        self.progress_manager = progress_manager

    async def handle_products_images_ready_batch(self, event_data: Dict[str, Any]):
        """Handle products images ready batch event to initialize job tracking"""
        try:
            job_id = event_data["job_id"]
            total_images = event_data["total_images"]
            
            logger.info("Batch event received",
                       job_id=job_id,
                       asset_type="image",
                       total_items=total_images,
                       event_type="products_images_ready_batch")
            
            # Store the total image count for the job
            self.progress_manager.job_image_counts[job_id] = {'total': total_images, 'processed': 0}
            logger.info("Batch tracking initialized",
                       job_id=job_id,
                       asset_type="image",
                       total_items=total_images)
            
            # Mark batch as initialized
            self.progress_manager._mark_batch_initialized(job_id, "image")
            
            # If there are no images, immediately publish completion event
            if total_images == 0:
                logger.info("Immediate completion for zero-asset job", job_id=job_id, asset_type="image")
                await self.progress_manager.publish_completion_event_with_count(job_id, "image", 0, 0, "embeddings")
            
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
            
            logger.info("Batch event received",
                       job_id=job_id,
                       asset_type="video",
                       total_items=total_keyframes,
                       event_type="videos_keyframes_ready_batch",
                       event_id=event_id)
            
            # Store the total frame count for the job
            self.progress_manager.expected_total_frames[job_id] = total_keyframes
            # Store the total frame count for the job
            self.progress_manager.job_frame_counts[job_id] = {'total': total_keyframes, 'processed': 0}
            logger.info("Batch tracking initialized",
                       job_id=job_id,
                       asset_type="video",
                       total_items=total_keyframes)
            
            # Mark batch as initialized
            self.progress_manager._mark_batch_initialized(job_id, "video")
            
            # If there are no keyframes, immediately publish completion event
            if total_keyframes == 0:
                logger.info("Immediate completion for zero-asset job", job_id=job_id, asset_type="video")
                await self.progress_manager.publish_completion_event_with_count(job_id, "video", 0, 0, "embeddings")
            
        except Exception as e:
            logger.error("Failed to handle videos keyframes ready batch",
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
            
            # Create a unique key for this asset
            asset_key = f"{job_id}:{image_id}"
            
            # Skip if we've already processed this asset
            if self.progress_manager.processed_assets.is_processed(asset_key):
                logger.info("Skipping duplicate asset", job_id=job_id, asset_id=image_id, asset_type="image")
                return
                
            # Add to processed assets
            self.progress_manager.processed_assets.add(asset_key)
            
            logger.info("Processing item",
                       job_id=job_id,
                       asset_id=image_id,
                       asset_type="image",
                       item_path=local_path)
            
            # Extract embeddings first
            emb_rgb, emb_gray = await self.extractor.extract_embeddings(local_path)
            
            if emb_rgb is not None and emb_gray is not None:
                # Update database with embeddings
                await self.image_crud.update_embeddings(image_id, emb_rgb.tolist(), emb_gray.tolist())
                
                # Emit image embedding ready event (per asset)
                event_id = str(uuid.uuid4())
                await self.broker.publish_event(
                    "image.embedding.ready",
                    {
                        "job_id": job_id,
                        "asset_id": image_id,
                        "event_id": event_id
                    }
                )
                
                logger.info("Item processed successfully",
                           job_id=job_id,
                           asset_id=image_id,
                           asset_type="image")
            else:
                logger.error("Item processing failed",
                            job_id=job_id,
                            asset_id=image_id,
                            asset_type="image",
                            error="Failed to extract embeddings")
                return
            
            # Update job progress tracking only if we have job counts initialized
            job_counts = self.progress_manager.job_image_counts.get(job_id)
            if not job_counts:
                logger.warning("Job counts not initialized for job, skipping completion tracking", job_id=job_id)
                return
                
            # Check if batch has been initialized
            if not self.progress_manager._is_batch_initialized(job_id, "image"):
                logger.warning("Batch not initialized for job, skipping completion tracking", job_id=job_id)
                return
                
            # Increment processed count
            self.progress_manager.job_image_counts[job_id]['processed'] += 1
            current_count = self.progress_manager.job_image_counts[job_id]['processed']
            total_count = self.progress_manager.job_image_counts[job_id]['total']
            
            logger.debug("Progress update",
                        job_id=job_id,
                        asset_type="image",
                        processed=current_count,
                        total=total_count)
            
            # Check if all images are processed
            if current_count >= total_count:
                logger.info("Batch completed",
                           job_id=job_id,
                           asset_type="image",
                           processed=current_count,
                           total=total_count)
                
                # Publish completion event
                await self.progress_manager.publish_completion_event_with_count(
                    job_id, "image", total_count, current_count, "embeddings"
                )
                
                # Clean up job tracking
                self.progress_manager._cleanup_job_tracking(job_id)
                logger.info("Removed job from tracking", job_id=job_id)
                
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
            
            # Use expected_total_frames from batch event if available, otherwise use frame count
            expected_count = self.progress_manager.expected_total_frames.get(job_id, len(frames))
            
            logger.info("Starting batch processing",
                       job_id=job_id,
                       asset_type="video",
                       total_items=len(frames),
                       expected_count=expected_count)
            
            # Check if batch has been initialized
            if not self.progress_manager._is_batch_initialized(job_id, "video"):
                logger.warning("Batch not initialized for job, skipping completion tracking", job_id=job_id)
                return
            
            # Initialize job progress with expected frame count from batch
            await self.progress_manager.update_job_progress(job_id, "video", expected_count, increment=0, event_type_prefix="embeddings")
            
            # Process each frame
            for frame_data in frames:
                frame_id = frame_data["frame_id"]
                local_path = frame_data["local_path"]
                
                # Create a unique key for this asset
                asset_key = f"{job_id}:{frame_id}"
                
                # Skip if we've already processed this asset
                if self.progress_manager.processed_assets.is_processed(asset_key):
                    logger.info("Skipping duplicate asset", job_id=job_id, asset_id=frame_id, asset_type="video")
                    continue
                    
                # Add to processed assets
                self.progress_manager.processed_assets.add(asset_key)
                
                logger.info("Processing item",
                           job_id=job_id,
                           asset_id=frame_id,
                           asset_type="video",
                           item_path=local_path)
                
                # Extract embeddings
                emb_rgb, emb_gray = await self.extractor.extract_embeddings(local_path)
                
                if emb_rgb is not None and emb_gray is not None:
                    # Update database with embeddings
                    await self.frame_crud.update_embeddings(frame_id, emb_rgb.tolist(), emb_gray.tolist())
                    
                    # Emit video embedding ready event (per asset)
                    event_id = str(uuid.uuid4())
                    await self.broker.publish_event(
                        "video.embedding.ready",
                        {
                            "job_id": job_id,
                            "asset_id": frame_id,
                            "event_id": event_id
                        }
                    )
                    
                    logger.info("Item processed successfully",
                               job_id=job_id,
                               asset_id=frame_id,
                               asset_type="video")
                    # Update job progress for successful processing using expected_total_frames
                    await self.progress_manager.update_job_progress(job_id, "video", expected_count, event_type_prefix="embeddings")
                    
                    # Update job frame counts tracking
                    if job_id in self.progress_manager.job_frame_counts:
                        self.progress_manager.job_frame_counts[job_id]['processed'] += 1
                        current_count = self.progress_manager.job_frame_counts[job_id]['processed']
                        total_count = self.progress_manager.job_frame_counts[job_id]['total']
                        
                        logger.debug("Progress update",
                                    job_id=job_id,
                                    asset_type="video",
                                    processed=current_count,
                                    total=total_count)
                        
                        # Check if all frames are processed
                        if current_count >= total_count:
                            logger.info("Batch completed",
                                       job_id=job_id,
                                       asset_type="video",
                                       processed=current_count,
                                       total=total_count)
                            
                            # Publish completion event
                            await self.progress_manager.publish_completion_event_with_count(
                                job_id, "video", total_count, current_count, "embeddings"
                            )
                            
                            # Clean up job tracking
                            self.progress_manager._cleanup_job_tracking(job_id)
                            logger.info("Removed job from tracking", job_id=job_id)
                else:
                    logger.error("Item processing failed",
                                job_id=job_id,
                                asset_id=frame_id,
                                asset_type="video",
                                error="Failed to extract embeddings")
        
        except Exception as e:
            logger.error("Batch processing failed",
                        job_id=job_id,
                        asset_type="video",
                        error=str(e),
                        error_type=type(e).__name__)
            raise    # New masked event handle
        
    async def handle_products_image_masked(self, event_data: Dict[str, Any]):
        """Handle product image masked event"""
        try:
            job_id = event_data["job_id"]
            image_id = event_data["image_id"]
            mask_path = event_data["mask_path"]
            
            # Create a unique key for this asset
            asset_key = f"{job_id}:{image_id}"
            
            # Skip if we've already processed this asset
            if self.progress_manager.processed_assets.is_processed(asset_key):
                logger.info("Skipping duplicate asset", job_id=job_id, asset_id=image_id, asset_type="image")
                return
                
            # Add to processed assets
            self.progress_manager.processed_assets.add(asset_key)
            
            logger.info("Processing item",
                       job_id=job_id,
                       asset_id=image_id,
                       asset_type="image",
                       item_path=mask_path,
                       operation="masked_processing")
            
            # Get the original image path from database
            image_record = await self.image_crud.get_by_id(image_id)
            if not image_record:
                logger.error("Resource not found",
                            job_id=job_id,
                            asset_id=image_id,
                            asset_type="image",
                            resource_type="image_record")
                return
            
            local_path = image_record.local_path
            
            # Extract embeddings with mask applied
            emb_rgb, emb_gray = await self.extractor.extract_embeddings_with_mask(local_path, mask_path)
            
            if emb_rgb is not None and emb_gray is not None:
                # Update database with embeddings
                await self.image_crud.update_embeddings(image_id, emb_rgb.tolist(), emb_gray.tolist())
                
                # Emit image embedding ready event (per asset)
                event_id = str(uuid.uuid4())
                await self.broker.publish_event(
                    "image.embedding.ready",
                    {
                        "job_id": job_id,
                        "asset_id": image_id,
                        "event_id": event_id
                    }
                )
                
                logger.info("Item processed successfully",
                           job_id=job_id,
                           asset_id=image_id,
                           asset_type="image")
            else:
                logger.error("Item processing failed",
                            job_id=job_id,
                            asset_id=image_id,
                            asset_type="image",
                            error="Failed to extract embeddings from masked image")
                return
            
            # Update job progress tracking only if we have job counts initialized
            job_counts = self.progress_manager.job_image_counts.get(job_id)
            if not job_counts:
                logger.warning("Job counts not initialized for job, skipping completion tracking", job_id=job_id)
                return
                
            # Check if batch has been initialized
            if not self.progress_manager._is_batch_initialized(job_id, "image"):
                logger.warning("Batch not initialized for job, skipping completion tracking", job_id=job_id)
                return
                
            # Increment processed count
            self.progress_manager.job_image_counts[job_id]['processed'] += 1
            current_count = self.progress_manager.job_image_counts[job_id]['processed']
            total_count = self.progress_manager.job_image_counts[job_id]['total']
            
            logger.debug("Progress update",
                        job_id=job_id,
                        asset_type="image",
                        processed=current_count,
                        total=total_count)
            
            # Check if all images are processed
            if current_count >= total_count:
                logger.info("Batch completed",
                           job_id=job_id,
                           asset_type="image",
                           processed=current_count,
                           total=total_count)
                
                # Publish completion event
                await self.progress_manager.publish_completion_event_with_count(
                    job_id, "image", total_count, current_count, "embeddings"
                )
                
                # Clean up job tracking
                self.progress_manager._cleanup_job_tracking(job_id)
                logger.info("Removed job from tracking", job_id=job_id)
                
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
            
            # Use expected_total_frames from batch event if available, otherwise use frame count
            expected_count = self.progress_manager.expected_total_frames.get(job_id, len(frames))
            
            logger.info("Starting batch processing",
                       job_id=job_id,
                       asset_type="video",
                       total_items=len(frames),
                       expected_count=expected_count,
                       operation="masked_processing")
            
            # Check if batch has been initialized
            if not self.progress_manager._is_batch_initialized(job_id, "video"):
                logger.warning("Batch not initialized for job, skipping completion tracking", job_id=job_id)
                return
            
            # Initialize job progress with expected frame count from batch
            await self.progress_manager.update_job_progress(job_id, "video", expected_count, increment=0, event_type_prefix="embeddings")
            
            # Process each frame
            for frame_data in frames:
                frame_id = frame_data["frame_id"]
                mask_path = frame_data["mask_path"]
                
                # Create a unique key for this asset
                asset_key = f"{job_id}:{frame_id}"
                
                # Skip if we've already processed this asset
                if self.progress_manager.processed_assets.is_processed(asset_key):
                    logger.info("Skipping duplicate asset", job_id=job_id, asset_id=frame_id, asset_type="video")
                    continue
                    
                # Add to processed assets
                self.progress_manager.processed_assets.add(asset_key)
                
                logger.info("Processing item",
                           job_id=job_id,
                           asset_id=frame_id,
                           asset_type="video",
                           item_path=mask_path,
                           operation="masked_processing")
                
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
                
                # Extract embeddings with mask applied
                emb_rgb, emb_gray = await self.extractor.extract_embeddings_with_mask(local_path, mask_path)
                
                if emb_rgb is not None and emb_gray is not None:
                    # Update database with embeddings
                    await self.frame_crud.update_embeddings(frame_id, emb_rgb.tolist(), emb_gray.tolist())
                    
                    # Emit video embedding ready event (per asset)
                    event_id = str(uuid.uuid4())
                    await self.broker.publish_event(
                        "video.embedding.ready",
                        {
                            "job_id": job_id,
                            "asset_id": frame_id,
                            "event_id": event_id
                        }
                    )
                    
                    logger.info("Item processed successfully",
                               job_id=job_id,
                               asset_id=frame_id,
                               asset_type="video")
                    # Update job progress for successful processing using expected_total_frames
                    await self.progress_manager.update_job_progress(job_id, "video", expected_count, event_type_prefix="embeddings")
                    
                    # Update job frame counts tracking
                    if job_id in self.progress_manager.job_frame_counts:
                        self.progress_manager.job_frame_counts[job_id]['processed'] += 1
                        current_count = self.progress_manager.job_frame_counts[job_id]['processed']
                        total_count = self.progress_manager.job_frame_counts[job_id]['total']
                        
                        logger.debug("Progress update",
                                    job_id=job_id,
                                    asset_type="video",
                                    processed=current_count,
                                    total=total_count)
                        
                        # Check if all frames are processed
                        if current_count >= total_count:
                            logger.info("Batch completed",
                                       job_id=job_id,
                                       asset_type="video",
                                       processed=current_count,
                                       total=total_count)
                            
                            # Publish completion event
                            await self.progress_manager.publish_completion_event_with_count(
                                job_id, "video", total_count, current_count, "embeddings"
                            )
                            
                            # Clean up job tracking
                            self.progress_manager._cleanup_job_tracking(job_id)
                            logger.info("Removed job from tracking", job_id=job_id)
                else:
                    logger.error("Item processing failed",
                                job_id=job_id,
                                asset_id=frame_id,
                                asset_type="video",
                                error="Failed to extract embeddings from masked frame")
        
        except Exception as e:
            logger.error("Batch processing failed",
                        job_id=job_id,
                        asset_type="video",
                        error=str(e),
                        error_type=type(e).__name__)
            raise
