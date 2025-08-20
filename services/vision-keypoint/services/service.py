from common_py.logging_config import configure_logging
from typing import Dict, Any, List, Optional
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from keypoint import KeypointExtractor
import uuid
import asyncio
from vision_common import JobProgressManager

logger = configure_logging("vision-keypoint")


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
    
    async def _publish_completion_event_with_count(self, job_id: str, asset_type: str, expected: int, done: int):
        await self.progress_manager.publish_completion_event_with_count(job_id, asset_type, expected, done, "keypoints")

    async def _update_and_check_completion_per_asset_first(self, job_id: str, asset_type: str):
        """Update progress and check if batch is complete (per-asset first pattern)"""
        # Initialize job tracking with high expected count if not already initialized
        if job_id not in self.progress_manager.job_tracking:
            logger.info("Initializing job tracking with high expected count (per-asset first)", job_id=job_id, asset_type=asset_type)
            await self.progress_manager.initialize_with_high_expected(job_id, asset_type)
        
        # Update job progress tracking
        await self.progress_manager.update_job_progress(job_id, asset_type, 0, increment=1, event_type_prefix="keypoints")
        
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
                is_complete = await self.progress_manager.update_expected_and_recheck_completion(job_id, asset_type, real_expected, "keypoints")
                
                if is_complete:
                    # Get current done count for completion event
                    job_data = self.progress_manager.job_tracking[job_id]
                    done_count = job_data["done"]
                    
                    # Publish completion event
                    await self.progress_manager.publish_completion_event_with_count(
                        job_id, asset_type, real_expected, done_count, "keypoints"
                    )
                    
                    # Clean up job tracking
                    self.progress_manager._cleanup_job_tracking(job_id)
                    logger.info("Removed job from tracking after per-asset first completion", job_id=job_id)
    
    
    async def handle_products_image_ready(self, event_data: Dict[str, Any]):
        """Handle product images ready event"""
        try:
            product_id = event_data["product_id"]
            image_id = event_data["image_id"]
            local_path = event_data["local_path"]
            job_id = event_data["job_id"]  # job_id is now required
            
            # DEBUG: Log individual asset event arrival
            logger.debug("DIAGNOSTIC: Individual asset event received",
                       job_id=job_id,
                       asset_id=image_id,
                       asset_type="image",
                       current_job_image_counts=list(self.progress_manager.job_image_counts.keys()),
                       has_batch_initialized=job_id in getattr(self.progress_manager.base_manager, 'job_batch_initialized', {}))
            
            # Create a unique key for this asset
            asset_key = f"{job_id}:{image_id}"
            
            # Skip if we've already processed this asset
            if asset_key in self.progress_manager.processed_assets:
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
            
            # Update job progress tracking using per-asset first pattern
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
                
                # Create a unique key for this asset
                asset_key = f"{job_id}:{frame_id}"
                
                # Skip if we've already processed this asset
                if asset_key in self.progress_manager.processed_assets:
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
                    # Update job progress for successful processing using per-asset first pattern
                    await self._update_and_check_completion_per_asset_first(job_id, "video")
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
            
            # DEBUG: Log individual masked asset event arrival
            logger.debug("DIAGNOSTIC: Individual masked asset event received",
                       job_id=job_id,
                       asset_id=image_id,
                       asset_type="image",
                       current_job_image_counts=list(self.progress_manager.job_image_counts.keys()),
                       has_batch_initialized=job_id in getattr(self.progress_manager.base_manager, 'job_batch_initialized', {}))
            
            # Create a unique key for this asset
            asset_key = f"{job_id}:{image_id}"
            
            # Skip if we've already processed this asset
            if asset_key in self.progress_manager.processed_assets:
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
            
            # Update job progress tracking using per-asset first pattern
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
                
                # Create a unique key for this asset
                asset_key = f"{job_id}:{frame_id}"
                
                # Skip if we've already processed this asset
                if asset_key in self.progress_manager.processed_assets:
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
                    # Update job progress for successful processing using per-asset first pattern
                    await self._update_and_check_completion_per_asset_first(job_id, "video")
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
            # DEBUG: Log batch event initialization
            logger.debug("DIAGNOSTIC: Masked batch event initialized job counts",
                       job_id=job_id,
                       asset_type="image",
                       total_images=total_images,
                       job_image_counts_keys=list(self.progress_manager.job_image_counts.keys()))
            
            # If there are no images, immediately publish completion event
            if total_images == 0:
                logger.info("Immediate completion for zero-asset job", job_id=job_id, asset_type="image")
                await self.progress_manager.publish_completion_event_with_count(job_id, "image", 0, 0, "keypoints")
            
            # Check if job is already complete (per-asset first scenario)
            if job_id in self.progress_manager.job_tracking:
                logger.info("Checking for completion after batch initialization", job_id=job_id, asset_type="image", total_images=total_images)
                is_complete = await self.progress_manager.update_expected_and_recheck_completion(job_id, "image", total_images, "keypoints")
                if is_complete:
                    logger.info("Job completed after batch initialization", job_id=job_id, asset_type="image", total_images=total_images)
            
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
            self.progress_manager.job_frame_counts[job_id] = {'total': total_keyframes, 'processed': 0}
            logger.info("Batch tracking initialized",
                       job_id=job_id,
                       asset_type="video",
                       total_items=total_keyframes)
            
            # If there are no keyframes, immediately publish completion event
            if total_keyframes == 0:
                logger.info("Immediate completion for zero-asset job", job_id=job_id, asset_type="video")
                await self.progress_manager.publish_completion_event_with_count(job_id, "video", 0, 0, "keypoints")
            
            # Check if job is already complete (per-asset first scenario)
            if job_id in self.progress_manager.job_tracking:
                logger.info("Checking for completion after batch initialization", job_id=job_id, asset_type="video", total_keyframes=total_keyframes)
                is_complete = await self.progress_manager.update_expected_and_recheck_completion(job_id, "video", total_keyframes, "keypoints")
                if is_complete:
                    logger.info("Job completed after batch initialization", job_id=job_id, asset_type="video", total_keyframes=total_keyframes)
            
        except Exception as e:
            logger.error("Failed to handle videos keyframes masked batch",
                        job_id=job_id,
                        event_id=event_data.get("event_id"),
                        error=str(e),
                        error_type=type(e).__name__)
            raise