"""Event emitter for product segmentor service."""

import uuid
from typing import List
from common_py.messaging import MessageBroker
from common_py.logging_config import configure_logging

from config_loader import config

logger = configure_logging("product-segmentor:event_emitter", config.LOG_LEVEL)


class EventEmitter:
    """Handles event emission with consistent logging and error handling."""
    
    def __init__(self, broker: MessageBroker):
        """Initialize event emitter.
        
        Args:
            broker: Message broker instance
        """
        self.broker = broker
    
    async def emit_product_image_masked(self, job_id: str, image_id: str, mask_path: str) -> None:
        """Emit product image masked event."""
        event_id = str(uuid.uuid4())
        event_data = {
            "event_id": event_id,
            "job_id": job_id,
            "image_id": image_id,
            "mask_path": mask_path
        }
        
        logger.info("Emitting product image masked event", job_id=job_id, image_id=image_id, event_id=event_id, mask_path=mask_path)
        
        try:
            await self.broker.publish_event("products.image.masked", event_data)
            logger.info("Successfully emitted product image masked event", job_id=job_id, image_id=image_id, event_id=event_id)
        except Exception as e:
            logger.error("Failed to emit product image masked event", job_id=job_id, image_id=image_id, event_id=event_id, error=str(e))
            raise
    
    async def emit_video_keyframes_masked(self, job_id: str, video_id: str, frames: List[dict]) -> None:
        """Emit video keyframes masked event."""
        event_id = str(uuid.uuid4())
        event_data = {
            "event_id": event_id,
            "job_id": job_id,
            "video_id": video_id,
            "frames": frames
        }
        
        logger.info("Emitting video keyframes masked event", job_id=job_id, video_id=video_id, frame_count=len(frames), event_id=event_id)
        
        try:
            await self.broker.publish_event("video.keyframes.masked", event_data)
            logger.info("Successfully emitted video keyframes masked event", job_id=job_id, video_id=video_id, frame_count=len(frames), event_id=event_id)
        except Exception as e:
            logger.error("Failed to emit video keyframes masked event", job_id=job_id, video_id=video_id, frame_count=len(frames), event_id=event_id, error=str(e))
            raise
    
    
