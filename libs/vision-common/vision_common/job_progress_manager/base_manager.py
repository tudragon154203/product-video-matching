import asyncio
import uuid
from typing import Dict, Any, Set, Optional
from common_py.logging_config import configure_logging
from common_py.messaging import MessageBroker

logger = configure_logging("job-progress-manager")

class BaseJobProgressManager:
    def __init__(self, broker: MessageBroker):
        self.broker = broker
        self.processed_assets: Set[str] = set()  # Track processed assets to avoid duplicates
        self.job_tracking: Dict[str, Dict] = {}  # Track job progress: {job_id: {expected: int, done: int, asset_type: str}}
        self.job_image_counts: Dict[str, Dict[str, int]] = {}  # Track job image counts: {job_id: {'total': int, 'processed': int}}
        self.job_frame_counts: Dict[str, Dict[str, int]] = {}  # Track job frame counts: {job_id: {'total': int, 'processed': int}}
        self.expected_total_frames: Dict[str, int] = {}  # Track expected total frames per job: {job_id: total_frames}
        self.processed_batch_events: set = set()  # Track processed batch events to avoid duplicates
        self.job_batch_initialized: Dict[str, set] = {}  # Track which batch types have been initialized for each job: {job_id: {asset_types}}

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
        """Update job progress and check for completion"""
        logger.debug("Updating job progress", job_id=job_id, asset_type=asset_type,
                     expected_count=expected_count, increment=increment,
                     current_job_tracking=self.job_tracking.get(job_id))
        # Initialize job tracking if not exists
        if job_id not in self.job_tracking:
            self.job_tracking[job_id] = {
                "expected": expected_count,
                "done": 0,
                "asset_type": asset_type
            }
        
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

    async def initialize_with_high_expected(self, job_id: str, asset_type: str, high_expected: int = 1000000):
        """Initialize job tracking with high expected count for per-asset first scenarios"""
        logger.debug("Initializing job with high expected count", job_id=job_id, asset_type=asset_type, high_expected=high_expected)
        
        # Initialize job tracking with high expected count
        if job_id not in self.job_tracking:
            self.job_tracking[job_id] = {
                "expected": high_expected,
                "done": 0,
                "asset_type": asset_type
            }
            logger.info("Job tracking initialized with high expected count", job_id=job_id, asset_type=asset_type, high_expected=high_expected)
        else:
            # Update existing job tracking with high expected count
            self.job_tracking[job_id]["expected"] = high_expected
            self.job_tracking[job_id]["asset_type"] = asset_type
            logger.info("Job tracking updated with high expected count", job_id=job_id, asset_type=asset_type, high_expected=high_expected)

    async def update_expected_and_recheck_completion(self, job_id: str, asset_type: str, real_expected: int, event_type_prefix: str = "embeddings"):
        """Update expected count with real value and re-check completion condition"""
        logger.debug("Updating expected count and re-checking completion", job_id=job_id, asset_type=asset_type, real_expected=real_expected)
        
        if job_id not in self.job_tracking:
            logger.warning("Job not found in tracking when updating expected count", job_id=job_id)
            return False
        
        job_data = self.job_tracking[job_id]
        current_done = job_data["done"]
        
        # Update expected count with real value
        job_data["expected"] = real_expected
        logger.debug("Updated expected count", job_id=job_id, old_expected=job_data["expected"], new_expected=real_expected, current_done=current_done)
        
        # Check if job is complete with new expected count
        if current_done >= real_expected:
            logger.info("Job completed after updating expected count", job_id=job_id, asset_type=asset_type, done=current_done, expected=real_expected)
            return True
        else:
            logger.debug("Job not complete after updating expected count", job_id=job_id, asset_type=asset_type, done=current_done, expected=real_expected)
            return False
