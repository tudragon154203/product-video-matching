"""Manages completion events for jobs using vision-common components."""

import asyncio
from typing import Dict, Set, Optional
from datetime import datetime, timedelta

from handlers.event_emitter import EventEmitter
from common_py.logging_config import configure_logging
from vision_common import JobProgressManager

logger = configure_logging("product-segmentor")


class CompletionManager:
    """Manages completion events for jobs using vision-common components."""
    
    def __init__(self, event_emitter: EventEmitter, job_progress_manager: JobProgressManager):
        """Initialize completion manager.
        
        Args:
            event_emitter: EventEmitter instance for publishing events
            job_progress_manager: JobProgressManager instance for progress tracking
        """
        self.event_emitter = event_emitter
        self.job_progress_manager = job_progress_manager
        self._completion_events_sent: Set[str] = set()
    
    def start_timer(self, job_id: str, timeout_seconds: int = 300) -> None:
        """Start a watermark timer for a job using vision-common.
        
        Args:
            job_id: Job identifier
            timeout_seconds: Timeout duration in seconds (default: 5 minutes)
        """
        # Use vision-common's watermark timer manager
        asyncio.create_task(self.job_progress_manager._start_watermark_timer(job_id, timeout_seconds, "segmentation"))
        logger.debug(f"Started watermark timer for job {job_id} ({timeout_seconds}s) using vision-common")
    
    def cancel_timer(self, job_id: str) -> None:
        """Cancel the watermark timer for a job using vision-common.
        
        Args:
            job_id: Job identifier
        """
        # Use vision-common's watermark timer manager
        self.job_progress_manager.watermark_timer_manager.cancel_watermark_timer(job_id)
        logger.debug(f"Cancelled watermark timer for job {job_id} using vision-common")
    
    async def finalize(
        self, 
        job_id: str, 
        counts: Dict[str, Dict[str, int]], 
        is_timeout: bool = False
    ) -> None:
        """Publish completion event for a job.
        
        Args:
            job_id: Job identifier
            counts: Progress counts with structure {'image': {'total': int, 'processed': int}, 'frame': {...}}
            is_timeout: Whether this is called due to timeout
        """
        completion_key = f"{job_id}:{'timeout' if is_timeout else 'normal'}"
        
        if completion_key in self._completion_events_sent:
            logger.debug(f"Completion event already sent for job {job_id}, skipping")
            return
        
        try:
            # Calculate completion percentages
            image_progress = counts.get('image', {'total': 0, 'processed': 0})
            frame_progress = counts.get('frame', {'total': 0, 'processed': 0})
            
            image_percent = 0
            if image_progress['total'] > 0:
                image_percent = (image_progress['processed'] / image_progress['total']) * 100
            
            frame_percent = 0
            if frame_progress['total'] > 0:
                frame_percent = (frame_progress['processed'] / frame_progress['total']) * 100
            
            # Determine overall completion status
            total_assets = image_progress['total'] + frame_progress['total']
            processed_assets = image_progress['processed'] + frame_progress['processed']
            
            if total_assets == 0:
                completion_percent = 100
            else:
                completion_percent = (processed_assets / total_assets) * 100
            
            # Publish completion event
            event_data = {
                "job_id": job_id,
                "completion_percent": completion_percent,
                "image_progress": image_progress,
                "frame_progress": frame_progress,
                "is_timeout": is_timeout,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Use appropriate completion method based on asset types
            if image_progress['total'] > 0 and frame_progress['total'] > 0:
                # Mixed assets - use generic completion or choose one based on business logic
                # For now, we'll use the products images completed method as fallback
                await self.event_emitter.emit_products_images_masked_completed(
                    job_id=job_id,
                    total_assets=total_assets,
                    processed_assets=processed_assets,
                    has_partial_completion=completion_percent < 100
                )
            elif image_progress['total'] > 0:
                # Only images
                await self.event_emitter.emit_products_images_masked_completed(
                    job_id=job_id,
                    total_assets=total_assets,
                    processed_assets=processed_assets,
                    has_partial_completion=completion_percent < 100
                )
            elif frame_progress['total'] > 0:
                # Only frames
                await self.event_emitter.emit_video_keyframes_masked_completed(
                    job_id=job_id,
                    total_assets=total_assets,
                    processed_assets=processed_assets,
                    has_partial_completion=completion_percent < 100
                )
            else:
                # No assets - immediate completion
                await self.event_emitter.emit_products_images_masked_completed(
                    job_id=job_id,
                    total_assets=0,
                    processed_assets=0,
                    has_partial_completion=False
                )
            self._completion_events_sent.add(completion_key)
            
            logger.info(
                f"Published completion event for job {job_id}: "
                f"{completion_percent:.1f}% complete "
                f"({processed_assets}/{total_assets} assets), "
                f"timeout={is_timeout}"
            )
            
        except Exception as e:
            logger.error(f"Error publishing completion event for job {job_id}: {e}")
    
    def mark_completion_sent(self, job_id: str, is_timeout: bool = False) -> None:
        """Mark completion event as sent without publishing.
        
        Args:
            job_id: Job identifier
            is_timeout: Whether this is for a timeout completion
        """
        completion_key = f"{job_id}:{'timeout' if is_timeout else 'normal'}"
        self._completion_events_sent.add(completion_key)
    
    def is_completion_sent(self, job_id: str, is_timeout: bool = False) -> bool:
        """Check if completion event was already sent for a job.
        
        Args:
            job_id: Job identifier
            is_timeout: Whether to check for timeout completion
            
        Returns:
            True if completion event was sent
        """
        completion_key = f"{job_id}:{'timeout' if is_timeout else 'normal'}"
        return completion_key in self._completion_events_sent
    
    def cleanup(self, job_id: str) -> None:
        """Cleanup resources for a job.
        
        Args:
            job_id: Job identifier
        """
        self.cancel_timer(job_id)
        # Clear both normal and timeout completion markers
        self._completion_events_sent.discard(f"{job_id}:normal")
        self._completion_events_sent.discard(f"{job_id}:timeout")
        # Use vision-common to cleanup job tracking
        self.job_progress_manager._cleanup_job_tracking(job_id)
        logger.debug(f"Cleaned up completion resources for job {job_id}")
    
    def cleanup_all(self) -> None:
        """Cleanup all resources."""
        # Cancel all timers using vision-common
        self.job_progress_manager.watermark_timer_manager.cleanup_all()
        
        # Clear all completion markers
        self._completion_events_sent.clear()
        logger.debug("Cleaned up all completion resources")
    
    async def publish_completion(self, job_id: str, progress_tracker=None) -> None:
        """Publish completion event for a job.
        
        Args:
            job_id: Job identifier
            progress_tracker: Deprecated parameter, kept for backward compatibility
        """
        try:
            # Use vision-common to publish completion event
            await self.job_progress_manager._publish_completion_event(job_id, False, "segmentation")
            
        except Exception as e:
            logger.error(f"Error publishing completion for job {job_id}: {e}")
            raise