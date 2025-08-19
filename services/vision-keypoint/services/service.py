from common_py.logging_config import configure_logging
from typing import Dict, Any, List, Optional
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from keypoint import KeypointExtractor
import uuid
import asyncio
from vision_common import JobProgressManager

logger = configure_logging("vision-keypoint.services")


class VisionKeypointService:
    """Main service class for vision keypoint extraction with progress tracking"""
    
    def __init__(self, db: DatabaseManager, broker: MessageBroker, data_root: str):
        self.db = db
        self.broker = broker
        self.extractor = KeypointExtractor(data_root)
        self.progress_manager = JobProgressManager(broker)
    
    async def cleanup(self):
        """Clean up resources"""
        await self.progress_manager.cleanup_all()
    
    async def _start_watermark_timer(self, job_id: str, ttl: int = 300):
        await self.progress_manager._start_watermark_timer(job_id, ttl, "keypoints")
    
    async def _publish_completion_event(self, job_id: str, is_timeout: bool = False):
        await self.progress_manager._publish_completion_event(job_id, is_timeout, "keypoints")
    
    async def _update_job_progress(self, job_id: str, asset_type: str, expected_count: int, increment: int = 1):
        await self.progress_manager.update_job_progress(job_id, asset_type, expected_count, increment, "keypoints")
    
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
            
            # If there are no images, immediately publish completion event
            if total_images == 0:
                logger.info("Immediate completion for zero-asset job", job_id=job_id, asset_type="image")
                await self.progress_manager.publish_completion_event_with_count(job_id, "image", 0, 0, "keypoints")
            
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
            # Store the total keyframe count for the job
            self.progress_manager.job_keyframe_counts[job_id] = {'total': total_keyframes, 'processed': 0}
            logger.info("Batch tracking initialized",
                       job_id=job_id,
                       asset_type="video",
                       total_items=total_keyframes)
            
            # If there are no keyframes, immediately publish completion event
            if total_keyframes == 0:
                logger.info("Immediate completion for zero-asset job", job_id=job_id, asset_type="video")
                await self.progress_manager.publish_completion_event_with_count(job_id, "video", 0, 0, "keypoints")
            
        except Exception as e:
            logger.error("Failed to handle videos keyframes ready batch",
                        job_id=job_id,
                        event_id=event_data.get("event_id"),
                        error=str(e),
                        error_type=type(e).__name__)
            raise
    
    async def _publish_completion_event_with_count(self, job_id: str, asset_type: str, expected: int, done: int):
        await self.progress_manager.publish_completion_event_with_count(job_id, asset_type, expected, done, "keypoints")
    
    
    async def handle_products_image_ready(self, event_data: Dict[str, Any]):
        """Handle product images ready event"""
        try:
            product_id = event_data["product_id"]
            image_id = event_data["image_id"]
            local_path = event_data["local_path"]
            job_id = event_data["job_id"]  # job_id is now required
            
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
                       item_path=local_path,
                       operation="keypoint_extraction")
            
            # Extract keypoints first
            kp_blob_path = await self.extractor.extract_keypoints(local_path, image_id)
            
            if kp_blob_path:
                # Update database with keypoint path
                await self.db.execute(
                    "UPDATE product_images SET kp_blob_path = $1 WHERE img_id = $2",
                    kp_blob_path, image_id
                )
                
                # Emit image keypoint ready event (per asset)
                event_id = str(uuid.uuid4())
                await self.broker.publish_event(
                    "image.keypoint.ready",
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
                            error="Failed to extract keypoints")
                return
            
            # Update job progress tracking only if we have job counts initialized
            job_counts = self.progress_manager.job_image_counts.get(job_id)
            if not job_counts:
                logger.warning("Job counts not initialized for job, skipping completion tracking", job_id=job_id)
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
                    job_id, "image", total_count, current_count, "keypoints"
                )
                
                # Remove job from tracking
                del self.progress_manager.job_image_counts[job_id]
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
                       expected_count=expected_count,
                       operation="keypoint_extraction")
            
            # Initialize job progress with expected frame count from batch
            await self.progress_manager.update_job_progress(job_id, "video", expected_count, increment=0)
            
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
                           item_path=local_path,
                           operation="keypoint_extraction")
                
                # Extract keypoints
                kp_blob_path = await self.extractor.extract_keypoints(local_path, frame_id)
                
                if kp_blob_path:
                    # Update database with keypoint path
                    await self.db.execute(
                        "UPDATE video_frames SET kp_blob_path = $1 WHERE frame_id = $2",
                        kp_blob_path, frame_id
                    )
                    
                    # Emit video keypoint ready event (per asset)
                    event_id = str(uuid.uuid4())
                    await self.broker.publish_event(
                        "video.keypoint.ready",
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
                    await self.progress_manager.update_job_progress(job_id, "video", expected_count, "keypoints")
                    
                    # Update job keyframe counts tracking
                    if job_id in self.progress_manager.job_keyframe_counts:
                        self.progress_manager.job_keyframe_counts[job_id]['processed'] += 1
                        current_count = self.progress_manager.job_keyframe_counts[job_id]['processed']
                        total_count = self.progress_manager.job_keyframe_counts[job_id]['total']
                        
                        logger.debug("Progress update",
                                    job_id=job_id,
                                    asset_type="video",
                                    processed=current_count,
                                    total=total_count)
                        
                        # Check if all keyframes are processed
                        if current_count >= total_count:
                            logger.info("Batch completed",
                                       job_id=job_id,
                                       asset_type="video",
                                       processed=current_count,
                                       total=total_count)
                            
                            # Publish completion event
                            await self.progress_manager.publish_completion_event_with_count(
                                job_id, "video", total_count, current_count, "keypoints"
                            )
                            
                            # Remove job from tracking
                            del self.progress_manager.job_keyframe_counts[job_id]
                            logger.info("Removed job from tracking", job_id=job_id)
                else:
                    logger.error("Item processing failed",
                                job_id=job_id,
                                asset_id=frame_id,
                                asset_type="video",
                                error="Failed to extract keypoints")
        except Exception as e:
            logger.error("Batch processing failed",
                        job_id=job_id,
                        asset_type="video",
                        error=str(e),
                        error_type=type(e).__name__)

    # New masked event handlers
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
            result = await self.db.fetch_one(
                "SELECT local_path FROM product_images WHERE img_id = $1",
                image_id
            )
            
            if not result:
                logger.error("Resource not found",
                            job_id=job_id,
                            asset_id=image_id,
                            asset_type="image",
                            resource_type="image_record")
                return
            
            local_path = result['local_path']
            
            # Extract keypoints with mask applied
            kp_blob_path = await self.extractor.extract_keypoints_with_mask(local_path, mask_path, image_id)
            
            if kp_blob_path:
                # Update database with keypoint path
                await self.db.execute(
                    "UPDATE product_images SET kp_blob_path = $1 WHERE img_id = $2",
                    kp_blob_path, image_id
                )
                
                # Emit image keypoint ready event (per asset)
                event_id = str(uuid.uuid4())
                await self.broker.publish_event(
                    "image.keypoint.ready",
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
                            error="Failed to extract keypoints from masked image")
                return
            
            # Update job progress tracking only if we have job counts initialized
            job_counts = self.progress_manager.job_image_counts.get(job_id)
            if not job_counts:
                logger.warning("Job counts not initialized for job, skipping completion tracking", job_id=job_id)
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
                    job_id, "image", total_count, current_count, "keypoints"
                )
                
                # Remove job from tracking
                del self.progress_manager.job_image_counts[job_id]
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
            
            # Initialize job progress with expected frame count from batch
            await self.progress_manager.update_job_progress(job_id, "video", expected_count, increment=0)
            
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
                result = await self.db.fetch_one(
                    "SELECT local_path FROM video_frames WHERE frame_id = $1",
                    frame_id
                )
                
                if not result:
                    logger.error("Resource not found",
                                job_id=job_id,
                                asset_id=frame_id,
                                asset_type="video",
                                resource_type="frame_record")
                    continue
                
                local_path = result['local_path']
                
                # Extract keypoints with mask applied
                kp_blob_path = await self.extractor.extract_keypoints_with_mask(local_path, mask_path, frame_id)
                
                if kp_blob_path:
                    # Update database with keypoint path
                    await self.db.execute(
                        "UPDATE video_frames SET kp_blob_path = $1 WHERE frame_id = $2",
                        kp_blob_path, frame_id
                    )
                    
                    # Emit video keypoint ready event (per asset)
                    event_id = str(uuid.uuid4())
                    await self.broker.publish_event(
                        "video.keypoint.ready",
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
                    await self.progress_manager.update_job_progress(job_id, "video", expected_count, "keypoints")
                    
                    # Update job keyframe counts tracking
                    if job_id in self.progress_manager.job_keyframe_counts:
                        self.progress_manager.job_keyframe_counts[job_id]['processed'] += 1
                        current_count = self.progress_manager.job_keyframe_counts[job_id]['processed']
                        total_count = self.progress_manager.job_keyframe_counts[job_id]['total']
                        
                        logger.debug("Progress update",
                                    job_id=job_id,
                                    asset_type="video",
                                    processed=current_count,
                                    total=total_count)
                        
                        # Check if all keyframes are processed
                        if current_count >= total_count:
                            logger.info("Batch completed",
                                       job_id=job_id,
                                       asset_type="video",
                                       processed=current_count,
                                       total=total_count)
                            
                            # Publish completion event
                            await self.progress_manager.publish_completion_event_with_count(
                                job_id, "video", total_count, current_count, "keypoints"
                            )
                            
                            # Remove job from tracking
                            del self.progress_manager.job_keyframe_counts[job_id]
                            logger.info("Removed job from tracking", job_id=job_id)
                else:
                    logger.error("Item processing failed",
                                job_id=job_id,
                                asset_id=frame_id,
                                asset_type="video",
                                error="Failed to extract keypoints from masked frame")
        
        except Exception as e:
            logger.error("Batch processing failed",
                        job_id=job_id,
                        asset_type="video",
                        error=str(e),
                        error_type=type(e).__name__)
            raise

    async def handle_products_images_masked_batch(self, event_data: Dict[str, Any]):
        """Handle products images masked batch event to initialize job tracking"""
        try:
            job_id = event_data["job_id"]
            total_images = event_data["total_images"]
            
            logger.info("Batch event received",
                       job_id=job_id,
                       asset_type="image",
                       total_items=total_images,
                       event_type="products_images_masked_batch")
            
            # Store the total image count for the job
            self.progress_manager.job_image_counts[job_id] = {'total': total_images, 'processed': 0}
            logger.info("Batch tracking initialized",
                       job_id=job_id,
                       asset_type="image",
                       total_items=total_images)
            
            # If there are no images, immediately publish completion event
            if total_images == 0:
                logger.info("Immediate completion for zero-asset job", job_id=job_id, asset_type="image")
                await self.progress_manager.publish_completion_event_with_count(job_id, "image", 0, 0, "keypoints")
            
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
            
            logger.info("Batch event received",
                       job_id=job_id,
                       asset_type="video",
                       total_items=total_keyframes,
                       event_type="videos_keyframes_masked_batch",
                       event_id=event_id)
            
            # Store the total keyframe count for the job
            self.progress_manager.expected_total_frames[job_id] = total_keyframes
            # Store the total keyframe count for the job
            self.progress_manager.job_keyframe_counts[job_id] = {'total': total_keyframes, 'processed': 0}
            logger.info("Batch tracking initialized",
                       job_id=job_id,
                       asset_type="video",
                       total_items=total_keyframes)
            
            # If there are no keyframes, immediately publish completion event
            if total_keyframes == 0:
                logger.info("Immediate completion for zero-asset job", job_id=job_id, asset_type="video")
                await self.progress_manager.publish_completion_event_with_count(job_id, "video", 0, 0, "keypoints")
            
        except Exception as e:
            logger.error("Failed to handle videos keyframes masked batch",
                        job_id=job_id,
                        event_id=event_data.get("event_id"),
                        error=str(e),
                        error_type=type(e).__name__)
            raise