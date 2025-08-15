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
        
        # Calculate partial completion flag
        has_partial = (done < expected) or (expected == 0)
        
        # Prepare event data
        event_id = str(uuid.uuid4())
        event_data = {
            "job_id": job_id,
            "event_id": event_id,
            "total_assets": expected,
            "processed_assets": done,
            "failed_assets": 0,  # Placeholder - actual failure tracking would be added separately
            "has_partial_completion": has_partial or is_timeout,
            "watermark_ttl": 300
        }
        
        # Publish appropriate event
        event_type = "image.keypoints.completed" if asset_type == "image" else "video.keypoints.completed"
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
        
        # Check completion condition
        job_data = self.job_tracking[job_id]
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
    
    async def _publish_completion_event_with_count(self, job_id: str, asset_type: str, expected: int, done: int):
        """Publish completion event with specific counts"""
        # Calculate partial completion flag
        has_partial = (done < expected) or (expected == 0)
        
        # Prepare event data
        event_id = str(uuid.uuid4())
        event_data = {
            "job_id": job_id,
            "event_id": event_id,
            "total_assets": expected,
            "processed_assets": done,
            "failed_assets": 0,  # Placeholder - actual failure tracking would be added separately
            "has_partial_completion": has_partial,
            "watermark_ttl": 300
        }
        
        # Publish appropriate event
        event_type = "image.keypoints.completed" if asset_type == "image" else "video.keypoints.completed"
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
    
    
    async def handle_products_images_ready(self, event_data: Dict[str, Any]):
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
            expected_count = event_data.get("expected_count", len(frames))  # Default to frame count if not provided
            
            logger.info("Processing video frame keypoints",
                       video_id=video_id, frame_count=len(frames), job_id=job_id)
            
            # Initialize job progress with expected frame count
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
                    # Update job progress for successful processing
                    await self._update_job_progress(job_id, "video", expected_count)
                else:
                    logger.error("Failed to extract keypoints", frame_id=frame_id)
        
        except Exception as e:
            logger.error("Failed to process video frame keypoints", error=str(e))
            raise