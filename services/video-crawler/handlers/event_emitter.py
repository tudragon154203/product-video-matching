import uuid
import logging
from typing import Dict, Any, Optional
from common_py.messaging import MessageBroker
from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler")


class EventEmitter:
    """Event emitter for video crawler service to delegate all event publishing"""
    
    def __init__(self, broker: MessageBroker):
        self.broker = broker
    
    async def publish_videos_keyframes_ready_batch(self, job_id: str, total_keyframes: int, correlation_id: Optional[str] = None):
        """Publish batch keyframes ready event"""
        batch_event_id = str(uuid.uuid4())
        await self.broker.publish_event(
            "videos.keyframes.ready.batch",
            {
                "job_id": job_id,
                "event_id": batch_event_id,
                "total_keyframes": total_keyframes
            },
            correlation_id=correlation_id or job_id
        )
        logger.info("Published batch keyframes ready event",
                   job_id=job_id,
                   total_keyframes=total_keyframes,
                   batch_event_id=batch_event_id)
        return batch_event_id
    
    async def publish_videos_collections_completed(self, job_id: str, correlation_id: Optional[str] = None):
        """Publish videos collections completed event"""
        event_id = str(uuid.uuid4())
        await self.broker.publish_event(
            "videos.collections.completed",
            {
                "job_id": job_id,
                "event_id": event_id
            },
            correlation_id=correlation_id or job_id
        )
        logger.info("Published videos collections completed event",
                   job_id=job_id,
                   event_id=event_id)
        return event_id
    
    async def publish_videos_keyframes_ready(self, video_id: str, frames: list, job_id: str, correlation_id: Optional[str] = None):
        """Publish individual video keyframes ready event"""
        await self.broker.publish_event(
            "videos.keyframes.ready",
            {
                "video_id": video_id,
                "frames": frames,
                "job_id": job_id
            },
            correlation_id=correlation_id or job_id
        )
        logger.info("Published video keyframes ready event",
                   video_id=video_id,
                   frame_count=len(frames),
                   job_id=job_id)
    
    async def publish_zero_asset_event(self, job_id: str, correlation_id: Optional[str] = None):
        """Publish event for zero assets case (no videos found)"""
        batch_event_id = str(uuid.uuid4())
        await self.broker.publish_event(
            "videos.keyframes.ready.batch",
            {
                "job_id": job_id,
                "event_id": batch_event_id,
                "total_keyframes": 0
            },
            correlation_id=correlation_id or job_id
        )
        logger.info("Published batch keyframes ready event with zero keyframes",
                   job_id=job_id,
                   total_keyframes=0,
                   batch_event_id=batch_event_id)
        return batch_event_id