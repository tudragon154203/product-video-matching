import structlog
from typing import Dict, Any, List, Optional
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import ProductImageCRUD, VideoFrameCRUD
from embedding import EmbeddingExtractor
import uuid
import asyncio

logger = structlog.get_logger()


class VisionEmbeddingService:
    """Main service class for vision embedding with progress tracking"""
    
    def __init__(self, db: DatabaseManager, broker: MessageBroker, embed_model: str):
        self.db = db
        self.broker = broker
        self.image_crud = ProductImageCRUD(db)
        self.frame_crud = VideoFrameCRUD(db)
        self.extractor = EmbeddingExtractor(embed_model)
        self.processed_assets = set()  # Track processed assets to avoid duplicates
        self.job_tracking: Dict[str, Dict] = {}  # Track job progress: {job_id: {expected: int, done: int, asset_type: str}}
        self.watermark_timers: Dict[str, asyncio.Task] = {}  # Watermark timers for jobs
        self.job_image_counts: Dict[str, Dict[str, int]] = {}  # Track job image counts: {job_id: {'total': int, 'processed': int}}
        self.job_frame_counts: Dict[str, Dict[str, int]] = {}  # Track job frame counts: {job_id: {'total': int, 'processed': int}}
        self.expected_total_frames: Dict[str, int] = {}  # Track expected total frames per job: {job_id: total_frames}
        self.processed_batch_events: set = set()  # Track processed batch events to avoid duplicates
    
    async def initialize(self):
        """Initialize the embedding extractor"""
        await self.extractor.initialize()
    
    async def cleanup(self):
        """Clean up resources"""
        await self.extractor.cleanup()
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
        
        # Prepare event data with idempotent flag to prevent duplicate completions
        event_id = str(uuid.uuid4())
        event_data = {
            "job_id": job_id,
            "event_id": event_id,
            "total_assets": expected,
            "processed_assets": done,
            "failed_assets": 0,  # Placeholder - actual failure tracking would be added separately
            "has_partial_completion": has_partial or is_timeout,
            "watermark_ttl": 300,
            "idempotent": True  # Flag to prevent duplicate completions
        }
        
        # Publish appropriate event - ensure only one completion event per job
        event_type = "image.embeddings.completed" if asset_type == "image" else "video.embeddings.completed"
        
        # Check if this job has already emitted a completion event
        if hasattr(self, '_completion_events_sent') and job_id in self._completion_events_sent:
            logger.info("Completion event already sent for job, skipping duplicate", job_id=job_id)
            return
            
        # Mark this job as having sent completion event
        if not hasattr(self, '_completion_events_sent'):
            self._completion_events_sent = set()
        self._completion_events_sent.add(job_id)
        
        await self.broker.publish_event(event_type, event_data)
        logger.info(f"Emitted {asset_type} embeddings completed event",
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
            # Store the total frame count for the job
            self.job_frame_counts[job_id] = {'total': total_keyframes, 'processed': 0}
            logger.info("DUPLICATE DETECTION: Initialized expected total frames", job_id=job_id, total_frames=total_keyframes, current_jobs_with_frames=len(self.expected_total_frames))
            logger.info("Initialized job frame counters", job_id=job_id, total_frames=total_keyframes)
            
            # If there are no keyframes, immediately publish completion event
            if total_keyframes == 0:
                logger.info("No keyframes found for job, publishing immediate completion", job_id=job_id)
                await self._publish_completion_event_with_count(job_id, "video", 0, 0)
            
        except Exception as e:
            logger.error("Failed to handle videos keyframes ready batch", job_id=job_id, event_id=event_data.get("event_id"), error=str(e))
            raise
    
    async def _publish_completion_event_with_count(self, job_id: str, asset_type: str, expected: int, done: int):
        """Publish completion event with specific counts"""
        # Calculate partial completion flag
        has_partial = (done < expected) or (expected == 0)
        
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
        
        # Publish appropriate event - ensure only one completion event per job
        event_type = "image.embeddings.completed" if asset_type == "image" else "video.embeddings.completed"
        
        # Check if this job has already emitted a completion event
        if hasattr(self, '_completion_events_sent'):
            if job_id in self._completion_events_sent:
                logger.warning("DUPLICATE DETECTION: Completion event already sent for job, skipping", job_id=job_id, asset_type=asset_type)
                return
        else:
            logger.debug("DUPLICATE DETECTION: _completion_events_sent set does not exist, creating it")
            self._completion_events_sent = set()
            
        # Mark this job as having sent completion event
        self._completion_events_sent.add(job_id)
        logger.info(f"DUPLICATE DETECTION: Marking job as completed", job_id=job_id, asset_type=asset_type, completed_jobs_count=len(self._completion_events_sent))
        
        await self.broker.publish_event(event_type, event_data)
        logger.info(f"Emitted {asset_type} embeddings completed event",
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
        if job_id in self.job_frame_counts:
            del self.job_frame_counts[job_id]
        if job_id in self.expected_total_frames:
            del self.expected_total_frames[job_id]
    
    
    async def handle_products_images_ready(self, event_data: Dict[str, Any]):
        """Handle product images ready event"""
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
            
            logger.info("Processing product image", image_id=image_id, job_id=job_id)
            
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
                
                logger.info("Processed product image embeddings", image_id=image_id)
            else:
                logger.error("Failed to extract embeddings", image_id=image_id)
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
            logger.error("Failed to process product image", error=str(e))
            raise
    
    async def handle_videos_keyframes_ready(self, event_data: Dict[str, Any]):
        """Handle video keyframes ready event"""
        try:
            video_id = event_data["video_id"]
            frames = event_data["frames"]
            job_id = event_data["job_id"]  # job_id is now required
            
            # Use expected_total_frames from batch event if available, otherwise use frame count
            expected_count = self.expected_total_frames.get(job_id, len(frames))
            
            logger.info("Processing video frames", video_id=video_id, frame_count=len(frames), job_id=job_id, expected_count=expected_count)
            
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
                
                logger.info("Processing video frame", frame_id=frame_id, job_id=job_id)
                
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
                    
                    logger.info("Processed video frame embeddings", frame_id=frame_id)
                    # Update job progress for successful processing using expected_total_frames
                    await self._update_job_progress(job_id, "video", expected_count)
                    
                    # Update job frame counts tracking
                    if job_id in self.job_frame_counts:
                        self.job_frame_counts[job_id]['processed'] += 1
                        current_count = self.job_frame_counts[job_id]['processed']
                        total_count = self.job_frame_counts[job_id]['total']
                        
                        logger.debug("Updated job frame counters", job_id=job_id,
                                   processed=current_count, total=total_count)
                        
                        # Check if all frames are processed
                        if current_count >= total_count:
                            logger.info("All frames processed for job", job_id=job_id,
                                       processed=current_count, total=total_count)
                            
                            # Publish completion event
                            await self._publish_completion_event_with_count(
                                job_id, "video", total_count, current_count
                            )
                            
                            # Remove job from tracking
                            del self.job_frame_counts[job_id]
                            logger.info("Removed job from tracking", job_id=job_id)
                else:
                    logger.error("Failed to extract embeddings", frame_id=frame_id)
        
        except Exception as e:
            logger.error("Failed to process video frames", error=str(e))
            raise