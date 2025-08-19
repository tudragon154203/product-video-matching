import asyncio
import uuid
from typing import Dict, Any, Set, Optional
from common_py.logging_config import configure_logging
from common_py.messaging import MessageBroker
from .job_progress_manager.base_manager import BaseJobProgressManager
from .job_progress_manager.watermark_timer_manager import WatermarkTimerManager
from .job_progress_manager.completion_event_publisher import CompletionEventPublisher

logger = configure_logging("job-progress-manager")

class JobProgressManager:
    """
    Manages job progress tracking, watermark timers, and completion event publishing
    for vision services.
    """

    def __init__(self, broker: MessageBroker):
        self.broker = broker
        self.base_manager = BaseJobProgressManager(broker)
        self.completion_publisher = CompletionEventPublisher(broker, self.base_manager)
        self.watermark_timer_manager = WatermarkTimerManager(self.completion_publisher)

    def _mark_batch_initialized(self, job_id: str, asset_type: str):
        self.base_manager._mark_batch_initialized(job_id, asset_type)

    def _is_batch_initialized(self, job_id: str, asset_type: str) -> bool:
        return self.base_manager._is_batch_initialized(job_id, asset_type)

    def _cleanup_job_tracking(self, job_id: str):
        self.base_manager._cleanup_job_tracking(job_id)
        self.watermark_timer_manager.cancel_watermark_timer(job_id)

    async def cleanup_all(self):
        await self.base_manager.cleanup_all()
        await self.watermark_timer_manager.cleanup_all()
        self.completion_publisher._completion_events_sent.clear()

    async def _start_watermark_timer(self, job_id: str, ttl: int = 300, event_type_prefix: str = "embeddings"):
        await self.watermark_timer_manager.start_watermark_timer(job_id, ttl, event_type_prefix)

    async def _publish_completion_event(self, job_id: str, is_timeout: bool = False, event_type_prefix: str = "embeddings"):
        await self.completion_publisher.publish_completion_event(job_id, is_timeout, event_type_prefix)

    async def update_job_progress(self, job_id: str, asset_type: str, expected_count: int, increment: int = 1, event_type_prefix: str = "embeddings"):
        await self.base_manager.update_job_progress(job_id, asset_type, expected_count, increment, event_type_prefix)
        # Check completion condition
        job_data = self.base_manager.job_tracking[job_id]
        if job_data["done"] >= job_data["expected"]:
            logger.debug("Completion condition met, attempting to publish event", job_id=job_id,
                         done=job_data["done"], expected=job_data["expected"])
            await self.completion_publisher.publish_completion_event(job_id, event_type_prefix=event_type_prefix)

    async def publish_completion_event_with_count(self, job_id: str, asset_type: str, expected: int, done: int, event_type_prefix: str = "embeddings"):
        await self.completion_publisher.publish_completion_event_with_count(job_id, asset_type, expected, done, event_type_prefix)

    @property
    def processed_assets(self) -> Set[str]:
        return self.base_manager.processed_assets

    @property
    def job_tracking(self) -> Dict[str, Dict]:
        return self.base_manager.job_tracking

    @property
    def watermark_timers(self) -> Dict[str, asyncio.Task]:
        return self.watermark_timer_manager.watermark_timers

    @property
    def job_image_counts(self) -> Dict[str, Dict[str, int]]:
        return self.base_manager.job_image_counts

    @property
    def job_frame_counts(self) -> Dict[str, Dict[str, int]]:
        return self.base_manager.job_frame_counts

    @property
    def expected_total_frames(self) -> Dict[str, int]:
        return self.base_manager.expected_total_frames

    @property
    def processed_batch_events(self) -> Set[str]:
        return self.base_manager.processed_batch_events

    @property
    def _completion_events_sent(self) -> Set[str]:
        return self.completion_publisher._completion_events_sent