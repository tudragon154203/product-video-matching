import structlog
from typing import Dict, Any, List, Optional
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from keypoint import KeypointExtractor
import uuid
import asyncio

logger = structlog.get_logger()


class VisionKeypointService:
    """Main service class for vision keypoint extraction with progress tracking"""
    
    def __init__(self, db: DatabaseManager, broker: MessageBroker, data_root: str):
        self.db = db
        self.broker = broker
        self.extractor = KeypointExtractor(data_root)
        self.processed_assets = set()  # Track processed assets to avoid duplicates
        self.job_tracking: Dict[str, Dict] = {}  # Track job progress: {job_id: {expected: int, done: int, asset_type: str}}
        self.watermark_timers: Dict[str, asyncio.Task] = {}  # Watermark timers for jobs
        self.job_image_counts: Dict[str, Dict[str, int]] = {}  # Track job image counts: {job_id: {'total': int, 'processed': int}}
        self.job_keyframe_counts: Dict[str, Dict[str, int]] = {}  # Track job keyframe counts: {job_id: {'total': int, 'processed': int}}
        self.expected_total_frames: Dict[str, int] = {}  # Track expected total frames per job: {job_id: total_frames}
        self.processed_batch_events: set = set()  # Track processed batch events to avoid duplicates
        self._completion_events_sent: set = set()  # Track jobs that have sent completion events to prevent duplicates
    
    async def cleanup(self):
        """Clean up resources"""
        # Cancel all watermark timers
        for timer in self.watermark_timers.values():
            timer.cancel()
    
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
        """Publish completion event with progress data"""
        if job_id not in self.job_tracking:
            logger.warning("Job not found in tracking", job_id=job_id)
            return
            
        job_data = self.job_tracking[job_id]
        asset_type = job_data["asset_type"]
        expected = job_data["expected"]
        done = job_data["done"]
        
        # Handle zero assets scenario
        if expected == 0:
            done = 0
            logger.info("Immediate completion for zero-asset job", job_id=job_id)
            has_partial = False  # For zero assets, there's no partial completion
        else:
            # Calculate partial completion flag
            has_partial = (done < expected)
        
        # Prepare event data - only required fields for keypoints schemas
        event_id = str(uuid.uuid4())
        event_data = {
            "job_id": job_id,
            "event_id": event_id
        }
        
        # Publish appropriate event - ensure only one completion event per job
        event_type = "image.keypoints.completed" if asset_type == "image" else "video.keypoints.completed"
        
        # Check if this job has already emitted a completion event for this specific asset_type
        # We need to track completion per asset_type (image/video) to allow separate events for embedding vs keypoint
        completion_key = f"{job_id}:{asset_type}"
        if completion_key in self._completion_events_sent:
            logger.info("Completion event already sent for this job and asset type, skipping duplicate",
                       job_id=job_id, asset_type=asset_type)
            return
            
        # Mark this job and asset_type as having sent completion event
        self._completion_events_sent.add(completion_key)
        
        await self.broker.publish_event(event_type, event_data)
        logger.info(f"Emitted {asset_type} keypoints completed event",
                   job_id=job_id, event_id=event_id,
                   total=expected, done=done, is_timeout=is_timeout)
        
        # Cleanup job tracking
        if job_id in self.job_tracking:
            del self.job_tracking[job_id]
        if job_id in self.watermark_timers:
            self.watermark_timers[job_id].cancel()
            del self.watermark_timers[job_id]
        if job_id in self.expected_total_frames:
            del self.expected_total_frames[job_id]
    
    async def _update_job_progress(self, job_id: str, asset_type: str, expected_count: int, increment: int = 1):
        """Update job progress and check for completion"""
        # Initialize job tracking if not exists
        if job_id not in self.job_tracking:
            self.job_tracking[job_id] = {
                "expected": expected_count,
                "done": 0,
                "asset_type": asset_type
            }
            # Start watermark timer on first asset
            await self._start_watermark_timer(job_id)
        
        # Update done count
        self.job_tracking[job_id]["done"] += increment
        
        # Check completion condition using expected_total_frames for video jobs
        job_data = self.job_tracking[job_id]
        actual_expected = expected_count
        
        # For video jobs, use expected_total_frames if available
        if asset_type == "video" and job_id in self.expected_total_frames:
            actual_expected = self.expected_total_frames[job_id]
            logger.debug("Using expected_total_frames for video job", job_id=job_id, expected=actual_expected)
        
        # Update expected count in tracking to match actual expected
        job_data["expected"] = actual_expected
        
        # Check completion condition
        if job_data["done"] >= job_data["expected"]:
            await self._publish_completion_event(job_id)
    
    async def handle_products_images_ready_batch(self, event_data: Dict[str, Any]):
        """Handle products images ready batch event to initialize job tracking"""
        try:
            job_id = event_data["job_id"]
            total_images = event_data["total_images"]
            
            logger.info("Products images ready batch received", job_id=job_id, total_images=total_images)
            
            # Store the total image count for the job
            self.job_image_counts[job_id] = {'total': total_images, 'processed': 0}
            logger.info("Initialized job image counters", job_id=job_id, total_images=total_images)
            
            # If there are no images, immediately publish completion event
            if total_images == 0:
                logger.info("No images found for job, publishing immediate completion", job_id=job_id)
                await self._publish_completion_event_with_count(job_id, "image", 0, 0)
            
        except Exception as e:
            logger.error("Failed to handle products images ready batch", job_id=job_id, error=str(e))
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
            if batch_event_key in self.processed_batch_events:
                logger.info("Ignoring duplicate batch event", job_id=job_id, event_id=event_id)
                return
            
            # Mark this batch event as processed
            self.processed_batch_events.add(batch_event_key)
            
            logger.info("Videos keyframes ready batch received", job_id=job_id, event_id=event_id, total_keyframes=total_keyframes)
            
            # Store the total frame count for the job
            self.expected_total_frames[job_id] = total_keyframes
            # Store the total keyframe count for the job
            self.job_keyframe_counts[job_id] = {'total': total_keyframes, 'processed': 0}
            logger.info("Initialized job keyframe counters", job_id=job_id, total_keyframes=total_keyframes)
            
            # If there are no keyframes, immediately publish completion event
            if total_keyframes == 0:
                logger.info("No keyframes found for job, publishing immediate completion", job_id=job_id)
                await self._publish_completion_event_with_count(job_id, "video", 0, 0)
            
        except Exception as e:
            logger.error("Failed to handle videos keyframes ready batch", job_id=job_id, event_id=event_data.get("event_id"), error=str(e))
            raise
    
    async def _publish_completion_event_with_count(self, job_id: str, asset_type: str, expected: int, done: int):
        """Publish completion event with specific counts"""
        # Handle zero assets scenario
        if expected == 0:
            has_partial = False  # For zero assets, there's no partial completion
        else:
            # Calculate partial completion flag
            has_partial = (done < expected)
        
        # Prepare event data - only required fields for keypoints schemas
        event_id = str(uuid.uuid4())
        event_data = {
            "job_id": job_id,
            "event_id": event_id
        }
        
        # Publish appropriate event - ensure only one completion event per job
        event_type = "image.keypoints.completed" if asset_type == "image" else "video.keypoints.completed"
        
        # Check if this job has already emitted a completion event for this specific asset_type
        completion_key = f"{job_id}:{asset_type}"
        if completion_key in self._completion_events_sent:
            logger.info("Completion event already sent for this job and asset type, skipping duplicate",
                       job_id=job_id, asset_type=asset_type)
            return
            
        # Mark this job and asset_type as having sent completion event
        self._completion_events_sent.add(completion_key)
        
        await self.broker.publish_event(event_type, event_data)
        logger.info(f"Emitted {asset_type} keypoints completed event",
                   job_id=job_id, event_id=event_id,
                   total=expected, done=done, is_timeout=False)
        
        # Cleanup job tracking
        if job_id in self.job_tracking:
            del self.job_tracking[job_id]
        if job_id in self.watermark_timers:
            self.watermark_timers[job_id].cancel()
            del self.watermark_timers[job_id]
        if job_id in self.job_image_counts:
            del self.job_image_counts[job_id]
        if job_id in self.job_keyframe_counts:
            del self.job_keyframe_counts[job_id]
        if job_id in self.expected_total_frames:
            del self.expected_total_frames[job_id]
    
    
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
            if asset_key in self.processed_assets:
                logger.info("Skipping duplicate asset", image_id=image_id, job_id=job_id)
                return
                
            # Add to processed assets
            self.processed_assets.add(asset_key)
            
            logger.info("Processing product image keypoints", image_id=image_id, job_id=job_id)
            
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
                
                logger.info("Processed product image keypoints",
                           image_id=image_id, kp_path=kp_blob_path)
            else:
                logger.error("Failed to extract keypoints", image_id=image_id)
                return
            
            # Update job progress tracking only if we have job counts initialized
            job_counts = self.job_image_counts.get(job_id)
            if not job_counts:
                logger.warning("Job counts not initialized for job, skipping completion tracking", job_id=job_id)
                return
                
            # Increment processed count
            self.job_image_counts[job_id]['processed'] += 1
            current_count = self.job_image_counts[job_id]['processed']
            total_count = self.job_image_counts[job_id]['total']
            
            logger.debug("Updated job image counters", job_id=job_id,
                       processed=current_count, total=total_count)
            
            # Check if all images are processed
            if current_count >= total_count:
                logger.info("All images processed for job", job_id=job_id,
                           processed=current_count, total=total_count)
                
                # Publish completion event
                await self._publish_completion_event_with_count(
                    job_id, "image", total_count, current_count
                )
                
                # Remove job from tracking
                del self.job_image_counts[job_id]
                logger.info("Removed job from tracking", job_id=job_id)
                
        except Exception as e:
            logger.error("Failed to process product image keypoints", error=str(e))
            raise
    
    async def handle_videos_keyframes_ready(self, event_data: Dict[str, Any]):
        """Handle video keyframes ready event"""
        try:
            video_id = event_data["video_id"]
            frames = event_data["frames"]
            job_id = event_data["job_id"]  # job_id is now required
            
            # Use expected_total_frames from batch event if available, otherwise use frame count
            expected_count = self.expected_total_frames.get(job_id, len(frames))
            
            logger.info("Processing video frame keypoints",
                       video_id=video_id, frame_count=len(frames), job_id=job_id, expected_count=expected_count)
            
            # Initialize job progress with expected frame count from batch
            await self._update_job_progress(job_id, "video", expected_count, increment=0)
            
            # Process each frame
            for frame_data in frames:
                frame_id = frame_data["frame_id"]
                local_path = frame_data["local_path"]
                
                # Create a unique key for this asset
                asset_key = f"{job_id}:{frame_id}"
                
                # Skip if we've already processed this asset
                if asset_key in self.processed_assets:
                    logger.info("Skipping duplicate asset", frame_id=frame_id, job_id=job_id)
                    continue
                    
                # Add to processed assets
                self.processed_assets.add(asset_key)
                
                logger.info("Processing video frame keypoints", frame_id=frame_id, job_id=job_id)
                
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
                    
                    logger.info("Processed video frame keypoints",
                               frame_id=frame_id, kp_path=kp_blob_path)
                    # Update job progress for successful processing using expected_total_frames
                    await self._update_job_progress(job_id, "video", expected_count)
                    
                    # Update job keyframe counts tracking
                    if job_id in self.job_keyframe_counts:
                        self.job_keyframe_counts[job_id]['processed'] += 1
                        current_count = self.job_keyframe_counts[job_id]['processed']
                        total_count = self.job_keyframe_counts[job_id]['total']
                        
                        logger.debug("Updated job keyframe counters", job_id=job_id,
                                   processed=current_count, total=total_count)
                        
                        # Check if all keyframes are processed
                        if current_count >= total_count:
                            logger.info("All keyframes processed for job", job_id=job_id,
                                       processed=current_count, total=total_count)
                            
                            # Publish completion event
                            await self._publish_completion_event_with_count(
                                job_id, "video", total_count, current_count
                            )
                            
                            # Remove job from tracking
                            del self.job_keyframe_counts[job_id]
                            logger.info("Removed job from tracking", job_id=job_id)
                else:
                    logger.error("Failed to extract keypoints", frame_id=frame_id)    
        except Exception as e:
            logger.error("Failed to process video frames", error=str(e))

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
            if asset_key in self.processed_assets:
                logger.info("Skipping duplicate masked asset", image_id=image_id, job_id=job_id)
                return
                
            # Add to processed assets
            self.processed_assets.add(asset_key)
            
            logger.info("Processing masked product image keypoints", image_id=image_id, job_id=job_id, mask_path=mask_path)
            
            # Get the original image path from database
            result = await self.db.fetch_one(
                "SELECT local_path FROM product_images WHERE img_id = $1",
                image_id
            )
            
            if not result:
                logger.error("Image record not found", image_id=image_id)
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
                
                logger.info("Processed masked product image keypoints", image_id=image_id, kp_path=kp_blob_path)
            else:
                logger.error("Failed to extract keypoints from masked image", image_id=image_id)
                return
            
            # Update job progress tracking only if we have job counts initialized
            job_counts = self.job_image_counts.get(job_id)
            if not job_counts:
                logger.warning("Job counts not initialized for job, skipping completion tracking", job_id=job_id)
                return
                
            # Increment processed count
            self.job_image_counts[job_id]['processed'] += 1
            current_count = self.job_image_counts[job_id]['processed']
            total_count = self.job_image_counts[job_id]['total']
            
            logger.debug("Updated job image counters", job_id=job_id,
                       processed=current_count, total=total_count)
            
            # Check if all images are processed
            if current_count >= total_count:
                logger.info("All masked images processed for job", job_id=job_id,
                           processed=current_count, total=total_count)
                
                # Publish completion event
                await self._publish_completion_event_with_count(
                    job_id, "image", total_count, current_count
                )
                
                # Remove job from tracking
                del self.job_image_counts[job_id]
                logger.info("Removed job from tracking", job_id=job_id)
                
        except Exception as e:
            logger.error("Failed to process masked product image keypoints", error=str(e))
            raise

    async def handle_video_keyframes_masked(self, event_data: Dict[str, Any]):
        """Handle video keyframes masked event"""
        try:
            job_id = event_data["job_id"]
            video_id = event_data["video_id"]
            frames = event_data["frames"]
            
            # Use expected_total_frames from batch event if available, otherwise use frame count
            expected_count = self.expected_total_frames.get(job_id, len(frames))
            
            logger.info("Processing masked video frame keypoints",
                       video_id=video_id, frame_count=len(frames), job_id=job_id, expected_count=expected_count)
            
            # Initialize job progress with expected frame count from batch
            await self._update_job_progress(job_id, "video", expected_count, increment=0)
            
            # Process each frame
            for frame_data in frames:
                frame_id = frame_data["frame_id"]
                mask_path = frame_data["mask_path"]
                
                # Create a unique key for this asset
                asset_key = f"{job_id}:{frame_id}"
                
                # Skip if we've already processed this asset
                if asset_key in self.processed_assets:
                    logger.info("Skipping duplicate masked asset", frame_id=frame_id, job_id=job_id)
                    continue
                    
                # Add to processed assets
                self.processed_assets.add(asset_key)
                
                logger.info("Processing masked video frame keypoints", frame_id=frame_id, job_id=job_id, mask_path=mask_path)
                
                # Get the original frame path from database
                result = await self.db.fetch_one(
                    "SELECT local_path FROM video_frames WHERE frame_id = $1",
                    frame_id
                )
                
                if not result:
                    logger.error("Frame record not found", frame_id=frame_id)
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
                    
                    logger.info("Processed masked video frame keypoints",
                               frame_id=frame_id, kp_path=kp_blob_path)
                    # Update job progress for successful processing using expected_total_frames
                    await self._update_job_progress(job_id, "video", expected_count)
                    
                    # Update job keyframe counts tracking
                    if job_id in self.job_keyframe_counts:
                        self.job_keyframe_counts[job_id]['processed'] += 1
                        current_count = self.job_keyframe_counts[job_id]['processed']
                        total_count = self.job_keyframe_counts[job_id]['total']
                        
                        logger.debug("Updated job keyframe counters", job_id=job_id,
                                   processed=current_count, total=total_count)
                        
                        # Check if all keyframes are processed
                        if current_count >= total_count:
                            logger.info("All masked keyframes processed for job", job_id=job_id,
                                       processed=current_count, total=total_count)
                            
                            # Publish completion event
                            await self._publish_completion_event_with_count(
                                job_id, "video", total_count, current_count
                            )
                            
                            # Remove job from tracking
                            del self.job_keyframe_counts[job_id]
                            logger.info("Removed job from tracking", job_id=job_id)
                else:
                    logger.error("Failed to extract keypoints from masked frame", frame_id=frame_id)
        
        except Exception as e:
            logger.error("Failed to process masked video frame keypoints", error=str(e))
            raise

    async def handle_products_images_masked_batch(self, event_data: Dict[str, Any]):
        """Handle products images masked batch event to initialize job tracking"""
        try:
            job_id = event_data["job_id"]
            total_images = event_data["total_images"]
            
            logger.info("Products images masked batch received", job_id=job_id, total_images=total_images)
            
            # Store the total image count for the job
            self.job_image_counts[job_id] = {'total': total_images, 'processed': 0}
            logger.info("Initialized job image counters for masked batch", job_id=job_id, total_images=total_images)
            
            # If there are no images, immediately publish completion event
            if total_images == 0:
                logger.info("No masked images found for job, publishing immediate completion", job_id=job_id)
                await self._publish_completion_event_with_count(job_id, "image", 0, 0)
            
        except Exception as e:
            logger.error("Failed to handle products images masked batch", job_id=job_id, error=str(e))
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
            if batch_event_key in self.processed_batch_events:
                logger.info("Ignoring duplicate masked batch event", job_id=job_id, event_id=event_id)
                return
            
            # Mark this batch event as processed
            self.processed_batch_events.add(batch_event_key)
            
            logger.info("Videos keyframes masked batch received", job_id=job_id, event_id=event_id, total_keyframes=total_keyframes)
            
            # Store the total keyframe count for the job
            self.expected_total_frames[job_id] = total_keyframes
            # Store the total keyframe count for the job
            self.job_keyframe_counts[job_id] = {'total': total_keyframes, 'processed': 0}
            logger.info("Initialized job keyframe counters for masked batch", job_id=job_id, total_keyframes=total_keyframes)
            
            # If there are no keyframes, immediately publish completion event
            if total_keyframes == 0:
                logger.info("No masked keyframes found for job, publishing immediate completion", job_id=job_id)
                await self._publish_completion_event_with_count(job_id, "video", 0, 0)
            
        except Exception as e:
            logger.error("Failed to handle videos keyframes masked batch", job_id=job_id, event_id=event_data.get("event_id"), error=str(e))
            raise