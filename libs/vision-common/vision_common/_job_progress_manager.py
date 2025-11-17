import asyncio
import os
from typing import Dict, Set
from common_py.logging_config import configure_logging
from common_py.messaging import MessageBroker
from .job_progress_manager.base_manager import BaseJobProgressManager
from .job_progress_manager.watermark_timer_manager import WatermarkTimerManager
from .job_progress_manager.completion_event_publisher import CompletionEventPublisher

try:
    from config import config as global_config
except ImportError:
    try:
        from libs.config import config as global_config
    except ImportError:
        global_config = None

logger = configure_logging("vision-common:_job_progress_manager")


def _get_completion_threshold_percentage() -> int:
    """Resolve the completion threshold percentage from global config or environment."""
    if global_config and hasattr(global_config, "COMPLETION_THRESHOLD_PERCENTAGE"):
        return getattr(global_config, "COMPLETION_THRESHOLD_PERCENTAGE", 100)
    env_value = os.getenv("COMPLETION_THRESHOLD_PERCENTAGE")
    try:
        return int(env_value) if env_value is not None else 100
    except ValueError:
        logger.warning("Invalid COMPLETION_THRESHOLD_PERCENTAGE value, falling back to 100", value=env_value)
        return 100


class JobProgressManager:
    """
    Manages job progress tracking, watermark timers, and completion event publishing
    for vision services.
    """

    def __init__(self, broker: MessageBroker):
        self.broker = broker
        threshold_percentage = max(0, min(_get_completion_threshold_percentage(), 100))
        self.completion_threshold_percentage = threshold_percentage
        completion_threshold_ratio = threshold_percentage / 100 if threshold_percentage > 0 else 0.0
        self.base_manager = BaseJobProgressManager(broker, completion_threshold=completion_threshold_ratio)
        self.completion_publisher = CompletionEventPublisher(broker, self.base_manager)
        self.watermark_timer_manager = WatermarkTimerManager(self.completion_publisher, self.base_manager)

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

    async def _start_watermark_timer(self, job_id: str, ttl: int = 900, event_type_prefix: str = "embeddings"):
        await self.watermark_timer_manager.start_watermark_timer(job_id, ttl, event_type_prefix)

    async def _publish_completion_event(self, job_id: str, is_timeout: bool = False, event_type_prefix: str = "embeddings"):
        await self.completion_publisher.publish_completion_event(job_id, is_timeout, event_type_prefix)

    async def update_job_progress(self, job_id: str, asset_type: str, expected_count: int, increment: int = 1, event_type_prefix: str = "embeddings"):
        await self.base_manager.update_job_progress(job_id, asset_type, expected_count, increment, event_type_prefix)
        key = f"{job_id}:{asset_type}:{event_type_prefix}"
        job_data = self.base_manager.job_tracking.get(key)
        if not job_data:
            return
        current_expected = job_data["expected"]
        if current_expected == 0 or current_expected >= 1000000:
            logger.debug("Skipping completion check - expected not finalized",
                        job_id=job_id, asset_type=asset_type, event_type_prefix=event_type_prefix,
                        expected=current_expected, done=job_data["done"])
            return
        if self.base_manager._has_reached_completion(job_data["done"], job_data["expected"]):
            done = job_data["done"]
            expected = job_data["expected"]
            logger.info("Automatic completion triggered by progress update",
                       job_id=job_id, asset_type=asset_type, event_type_prefix=event_type_prefix,
                       done=done, expected=expected,
                       completion_threshold_percentage=self.completion_threshold_percentage,
                       completion_trigger="update_job_progress",
                       current_completion_events_sent=len(self.completion_publisher._completion_events_sent))
            await self.completion_publisher.publish_completion_event_with_count(job_id, asset_type, expected, done, event_type_prefix)

    async def publish_completion_event_with_count(self, job_id: str, asset_type: str, expected: int, done: int, event_type_prefix: str = "embeddings"):
        await self.completion_publisher.publish_completion_event_with_count(job_id, asset_type, expected, done, event_type_prefix)

    async def publish_products_images_masked_batch(self, job_id: str, total_images: int) -> None:
        """Publish products images masked batch completion event."""
        await self.completion_publisher.publish_products_images_masked_batch(job_id, total_images)

    async def publish_videos_keyframes_masked_batch(self, job_id: str, total_keyframes: int) -> None:
        """Publish videos keyframes masked batch completion event."""
        await self.completion_publisher.publish_videos_keyframes_masked_batch(job_id, total_keyframes)

    async def publish_videos_keyframes_ready_batch(self, job_id: str, total_keyframes: int) -> None:
        """Publish videos keyframes ready batch completion event."""
        await self.completion_publisher.publish_videos_keyframes_ready_batch(job_id, total_keyframes)

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

    async def initialize_with_high_expected(self, job_id: str, asset_type: str, high_expected: int = 1000000, event_type_prefix: str = "embeddings"):
        """Initialize tracking with high expected for per-asset-first"""
        await self.base_manager.initialize_with_high_expected(job_id, asset_type, high_expected, event_type_prefix)

    async def update_expected_and_recheck_completion(self, job_id: str, asset_type: str, real_expected: int, event_type_prefix: str = "embeddings"):
        completion_detected = await self.base_manager.update_expected_and_recheck_completion(job_id, asset_type, real_expected, event_type_prefix)
        if completion_detected:
            key = f"{job_id}:{asset_type}:{event_type_prefix}"
            job_data = self.base_manager.job_tracking.get(key, {"done": 0, "expected": real_expected})
            done = job_data["done"]
            expected = job_data["expected"]
            logger.info("Completion detected, publishing completion event", job_id=job_id, asset_type=asset_type, event_type_prefix=event_type_prefix)
            await self.completion_publisher.publish_completion_event_with_count(job_id, asset_type, expected, done, event_type_prefix)
        return completion_detected
