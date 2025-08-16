"""Manages completion events and watermark timers for jobs."""

import asyncio
import logging
from typing import Dict, Set, Optional
from datetime import datetime, timedelta

from handlers.event_emitter import EventEmitter


logger = logging.getLogger(__name__)


class CompletionManager:
    """Manages completion events and watermark timers for jobs."""
    
    def __init__(self, event_emitter: EventEmitter):
        """Initialize completion manager.
        
        Args:
            event_emitter: EventEmitter instance for publishing events
        """
        self.event_emitter = event_emitter
        self._watermark_timers: Dict[str, asyncio.Task] = {}
        self._completion_events_sent: Set[str] = set()
    
    def start_timer(self, job_id: str, timeout_seconds: int = 300) -> None:
        """Start a watermark timer for a job.
        
        Args:
            job_id: Job identifier
            timeout_seconds: Timeout duration in seconds (default: 5 minutes)
        """
        if job_id in self._watermark_timers:
            # Timer already exists, cancel it first
            self._watermark_timers[job_id].cancel()
        
        async def _watermark_timer():
            """Timer task that publishes completion event on timeout."""
            try:
                await asyncio.sleep(timeout_seconds)
                logger.info(f"Watermark timer expired for job {job_id}, publishing completion event")
                await self.finalize(job_id, is_timeout=True)
            except asyncio.CancelledError:
                logger.debug(f"Watermark timer cancelled for job {job_id}")
            except Exception as e:
                logger.error(f"Error in watermark timer for job {job_id}: {e}")
        
        self._watermark_timers[job_id] = asyncio.create_task(_watermark_timer())
        logger.debug(f"Started watermark timer for job {job_id} ({timeout_seconds}s)")
    
    def cancel_timer(self, job_id: str) -> None:
        """Cancel the watermark timer for a job.
        
        Args:
            job_id: Job identifier
        """
        if job_id in self._watermark_timers:
            self._watermark_timers[job_id].cancel()
            del self._watermark_timers[job_id]
            logger.debug(f"Cancelled watermark timer for job {job_id}")
    
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
        logger.debug(f"Cleaned up completion resources for job {job_id}")
    
    def cleanup_all(self) -> None:
        """Cleanup all resources."""
        # Cancel all timers
        for job_id in list(self._watermark_timers.keys()):
            self.cancel_timer(job_id)
        
        # Clear all completion markers
        self._completion_events_sent.clear()
        logger.debug("Cleaned up all completion resources")
    
    async def publish_completion(self, job_id: str, progress_tracker) -> None:
        """Publish completion event for a job.
        
        Args:
            job_id: Job identifier
            progress_tracker: ProgressTracker instance
        """
        try:
            # Get job progress from progress tracker
            counts = progress_tracker.get_job_counts(job_id)
            
            # Publish completion event
            await self.finalize(job_id, counts, is_timeout=False)
            
        except Exception as e:
            logger.error(f"Error publishing completion for job {job_id}: {e}")
            raise