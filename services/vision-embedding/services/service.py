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
        event_type = "image.embeddings.completed" if asset_type == "image" else "video.embeddings.completed"
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
    
    
    async def handle_products_images_ready(self, event_data: Dict[str, Any]):
        """Handle product images ready event"""
        try:
            product_id = event_data["product_id"]
            image_id = event_data["image_id"]
            local_path = event_data["local_path"]
            job_id = event_data.get("job_id", "unknown")
            expected_count = event_data.get("expected_count", 1)  # Default to 1 if not provided
            
            # Create a unique key for this asset
            asset_key = f"{job_id}:{image_id}"
            
            # Skip if we've already processed this asset
            if asset_key in self.processed_assets:
                logger.info("Skipping duplicate asset", image_id=image_id, job_id=job_id)
                return
                
            # Add to processed assets
            self.processed_assets.add(asset_key)
            
            logger.info("Processing product image", image_id=image_id, job_id=job_id)
            
            # Initialize or update job progress
            await self._update_job_progress(job_id, "image", expected_count)
            
            # Extract embeddings
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
                
        except Exception as e:
            logger.error("Failed to process product image", error=str(e))
            raise
    
    async def handle_videos_keyframes_ready(self, event_data: Dict[str, Any]):
        """Handle video keyframes ready event"""
        try:
            video_id = event_data["video_id"]
            frames = event_data["frames"]
            job_id = event_data.get("job_id", "unknown")
            expected_count = event_data.get("expected_count", len(frames))  # Default to frame count if not provided
            
            logger.info("Processing video frames", video_id=video_id, frame_count=len(frames), job_id=job_id)
            
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
                    # Update job progress for successful processing
                    await self._update_job_progress(job_id, "video", expected_count)
                else:
                    logger.error("Failed to extract embeddings", frame_id=frame_id)
        
        except Exception as e:
            logger.error("Failed to process video frames", error=str(e))
            raise