from typing import Dict, Set
from common_py.logging_config import configure_logging
from common_py.messaging import MessageBroker

logger = configure_logging("vision-common:base_manager")


class BaseJobProgressManager:
    def __init__(self, broker: MessageBroker, completion_threshold: float = 1.0):
        self.broker = broker
        self.completion_threshold = max(0.0, min(completion_threshold, 1.0))
        self.processed_assets: Set[str] = set()
        # Track per (job_id, asset_type, event_type_prefix)
        self.job_tracking: Dict[str, Dict] = {}
        self.job_image_counts: Dict[str, Dict[str, int]] = {}
        self.job_frame_counts: Dict[str, Dict[str, int]] = {}
        self.expected_total_frames: Dict[str, int] = {}
        self.processed_batch_events: set = set()
        self.job_batch_initialized: Dict[str, set] = {}
    def _mark_batch_initialized(self, job_id: str, asset_type: str):
        """Mark a batch as initialized for a job"""
        if job_id not in self.job_batch_initialized:
            self.job_batch_initialized[job_id] = set()
        self.job_batch_initialized[job_id].add(asset_type)
        logger.debug("Marked batch as initialized", job_id=job_id, asset_type=asset_type)

    def _is_batch_initialized(self, job_id: str, asset_type: str) -> bool:
        """Check if a batch has been initialized for a job"""
        return job_id in self.job_batch_initialized and asset_type in self.job_batch_initialized[job_id]

    def _cleanup_job_tracking(self, job_id: str):
        """Clean up all tracking data for a job"""
        if job_id in self.job_tracking:
            del self.job_tracking[job_id]
        if job_id in self.expected_total_frames:
            del self.expected_total_frames[job_id]
        if job_id in self.job_image_counts:
            del self.job_image_counts[job_id]
        if job_id in self.job_frame_counts:
            del self.job_frame_counts[job_id]
        if job_id in self.job_batch_initialized:
            del self.job_batch_initialized[job_id]

    async def cleanup_all(self):
        """Clean up all resources (for service shutdown)"""
        self.processed_assets.clear()
        self.job_tracking.clear()
        self.job_image_counts.clear()
        self.job_frame_counts.clear()
        self.expected_total_frames.clear()
        self.processed_batch_events.clear()
        self.job_batch_initialized.clear()

    async def update_job_progress(self, job_id: str, asset_type: str, expected_count: int, increment: int = 1, event_type_prefix: str = "embeddings"):
        """Update job progress and check for completion (per asset type/prefix)"""
        key = f"{job_id}:{asset_type}:{event_type_prefix}"
        logger.debug("Updating job progress", job_id=job_id, asset_type=asset_type,
                     expected_count=expected_count, increment=increment,
                     event_type_prefix=event_type_prefix,
                     current_job_tracking=self.job_tracking.get(key))
        if key not in self.job_tracking:
            self.job_tracking[key] = {"expected": expected_count, "done": 0}
        self.job_tracking[key]["done"] += increment
        job_data = self.job_tracking[key]
        actual_expected = expected_count

        # For video jobs, use expected_total_frames if available
        if asset_type == "video" and job_id in self.expected_total_frames:
            actual_expected = self.expected_total_frames[job_id]
            logger.debug("Using expected_total_frames for video job", job_id=job_id, expected=actual_expected)
        current_expected = job_data["expected"]
        should_update_expected = (
            (0 < actual_expected < 1000000) or
            (current_expected >= 1000000 and 0 < actual_expected < 1000000) or
            (actual_expected == 0 and current_expected == 0)
        )
        if should_update_expected:
            job_data["expected"] = actual_expected
            logger.debug("Updated expected count", job_id=job_id, old_expected=current_expected, new_expected=actual_expected,
                         asset_type=asset_type, event_type_prefix=event_type_prefix)
        else:
            logger.debug("Preserving existing expected count", job_id=job_id,
                         current_expected=current_expected, requested_expected=actual_expected,
                         asset_type=asset_type, event_type_prefix=event_type_prefix)

    async def initialize_with_high_expected(self, job_id: str, asset_type: str, high_expected: int = 1000000, event_type_prefix: str = "embeddings"):
        """Initialize tracking with high expected for per-asset-first"""
        key = f"{job_id}:{asset_type}:{event_type_prefix}"
        logger.debug("Initializing job with high expected count", job_id=job_id, asset_type=asset_type, high_expected=high_expected, event_type_prefix=event_type_prefix)
        if key not in self.job_tracking:
            self.job_tracking[key] = {"expected": high_expected, "done": 0}
            logger.info("Job tracking initialized with high expected count", job_id=job_id, asset_type=asset_type, high_expected=high_expected, event_type_prefix=event_type_prefix)
        else:
            self.job_tracking[key]["expected"] = high_expected
            logger.info("Job tracking updated with high expected count", job_id=job_id, asset_type=asset_type, high_expected=high_expected, event_type_prefix=event_type_prefix)

    async def update_expected_and_recheck_completion(self, job_id: str, asset_type: str, real_expected: int, event_type_prefix: str = "embeddings"):
        """Update expected count with real value and re-check completion"""
        key = f"{job_id}:{asset_type}:{event_type_prefix}"
        logger.debug("Updating expected and re-checking completion", job_id=job_id, asset_type=asset_type, real_expected=real_expected, event_type_prefix=event_type_prefix)
        if key not in self.job_tracking:
            logger.warning("Job not found in tracking when updating expected count", job_id=job_id, asset_type=asset_type, event_type_prefix=event_type_prefix)
            return False
        job_data = self.job_tracking[key]
        current_done = job_data["done"]
        job_data["expected"] = real_expected
        logger.debug("Updated expected count", job_id=job_id, new_expected=real_expected, current_done=current_done, asset_type=asset_type, event_type_prefix=event_type_prefix)
        if self._has_reached_completion(current_done, real_expected):
            logger.info("Job completed after updating expected count", job_id=job_id, asset_type=asset_type, done=current_done, expected=real_expected, event_type_prefix=event_type_prefix)
            return True
        logger.debug("Job not complete after updating expected count", job_id=job_id, asset_type=asset_type, done=current_done, expected=real_expected, event_type_prefix=event_type_prefix)
        return False

    def _has_reached_completion(self, done: int, expected: int) -> bool:
        """Determine whether the completion threshold has been met."""
        if expected <= 0:
            return done >= expected
        threshold_count = expected * self.completion_threshold
        return done >= threshold_count
