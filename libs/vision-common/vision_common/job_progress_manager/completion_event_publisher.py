import asyncio
import uuid
from typing import Dict, Any, Set, Optional
from common_py.logging_config import configure_logging
from common_py.messaging import MessageBroker

logger = configure_logging("job-progress-manager")

class CompletionEventPublisher:
    def __init__(self, broker: MessageBroker, base_manager):
        self.broker = broker
        self.base_manager = base_manager
        self._completion_events_sent: set = set()  # Track completion events sent to prevent duplicates

    async def publish_completion_event(self, job_id: str, is_timeout: bool = False, event_type_prefix: str = "embeddings"):
        """Publish completion event with progress data"""
        if job_id not in self.base_manager.job_tracking:
            logger.warning("Job not found in tracking", job_id=job_id)
            return
            
        job_data = self.base_manager.job_tracking[job_id]
        asset_type = job_data["asset_type"]
        expected = job_data["expected"]
        done = job_data["done"]
        
        # Handle zero assets scenario
        if expected == 0:
            done = 0
            logger.info("Immediate completion for zero-asset job", job_id=job_id)
            has_partial = False  # For zero assets, there's no partial completion
        else:
            # Calculate partial completion flag
            has_partial = (done < expected)
        
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
        event_type = f"image.{event_type_prefix}.completed" if asset_type == "image" else f"video.{event_type_prefix}.completed"
        
        # Check if this job has already emitted a completion event for this specific asset_type
        completion_key = f"{job_id}:{asset_type}:{event_type_prefix}"
        logger.debug("Checking for existing completion event", job_id=job_id, asset_type=asset_type,
                     completion_key_in_set=completion_key in self._completion_events_sent)
        if completion_key in self._completion_events_sent:
            logger.warning("DUPLICATE COMPLETION EVENT DETECTED - skipping",
                          job_id=job_id, asset_type=asset_type, event_type_prefix=event_type_prefix,
                          completion_key=completion_key, current_set_size=len(self._completion_events_sent)
                          )
            return
            
        # Mark this job and asset_type as having sent completion event
        self._completion_events_sent.add(completion_key)
        logger.debug("Marked completion event as sent", job_id=job_id, asset_type=asset_type,
                     completion_key=completion_key, total_set_size=len(self._completion_events_sent))
        
        await self.broker.publish_event(event_type, event_data)
        logger.info(f"Emitted {asset_type} {event_type_prefix} completed event",
                   job_id=job_id, event_id=event_id,
                   total=expected, done=done, is_timeout=is_timeout)
        
        # Cleanup job tracking
        self.base_manager._cleanup_job_tracking(job_id)

    async def publish_completion_event_with_count(self, job_id: str, asset_type: str, expected: int, done: int, event_type_prefix: str = "embeddings"):
        """Publish completion event with specific counts"""
        # Handle zero assets scenario
        if expected == 0:
            has_partial = False  # For zero assets, there's no partial completion
        else:
            # Calculate partial completion flag
            has_partial = (done < expected)
        
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
        event_type = f"image.{event_type_prefix}.completed" if asset_type == "image" else f"video.{event_type_prefix}.completed"
        
        # Check if this job has already emitted a completion event for this specific asset_type
        completion_key = f"{job_id}:{asset_type}:{event_type_prefix}"
        logger.debug("Checking for existing completion event", job_id=job_id, asset_type=asset_type,
                     completion_key_in_set=completion_key in self._completion_events_sent)
        if completion_key in self._completion_events_sent:
            logger.info("Completion event already sent for this job and asset type, skipping duplicate",
                       job_id=job_id, asset_type=asset_type)
            return
            
        # Mark this job and asset_type as having sent completion event
        self._completion_events_sent.add(completion_key)
        logger.debug("Added completion key to set", job_id=job_id, asset_type=asset_type,
                     current_set_size=len(self._completion_events_sent))
        
        await self.broker.publish_event(event_type, event_data)
        logger.info(f"Emitted {asset_type} {event_type_prefix} completed event",
                   job_id=job_id, event_id=event_id,
                   total=expected, done=done, is_timeout=False)
        
        # Cleanup job tracking
        self.base_manager._cleanup_job_tracking(job_id)

    async def publish_products_images_masked_batch(self, job_id: str, total_images: int) -> None:
        """Publish products images masked batch completion event.
        
        Args:
            job_id: Job identifier
            total_images: Total number of images processed
        """
        event_id = str(uuid.uuid4())
        event_data = {
            "event_id": event_id,
            "job_id": job_id,
            "total_images": total_images
        }
        
        # Check if this job has already emitted a completion event for products images
        completion_key = f"{job_id}:products.images.masked.batch"
        if completion_key in self._completion_events_sent:
            logger.info("Products images masked batch event already sent, skipping duplicate",
                       job_id=job_id, total_images=total_images)
            return
            
        # Mark this job as having sent the completion event
        self._completion_events_sent.add(completion_key)
        
        await self.broker.publish_event("products.images.masked.batch", event_data)
        logger.info(f"Emitted products images masked batch event",
                   job_id=job_id, event_id=event_id, total_images=total_images)

    async def publish_videos_keyframes_masked_batch(self, job_id: str, total_keyframes: int) -> None:
        """Publish videos keyframes masked batch completion event.
        
        Args:
            job_id: Job identifier
            total_keyframes: Total number of keyframes processed
        """
        event_id = str(uuid.uuid4())
        event_data = {
            "event_id": event_id,
            "job_id": job_id,
            "total_keyframes": total_keyframes
        }
        
        # Check if this job has already emitted a completion event for videos keyframes
        completion_key = f"{job_id}:video.keyframes.masked.batch"
        if completion_key in self._completion_events_sent:
            logger.info("Videos keyframes masked batch event already sent, skipping duplicate",
                       job_id=job_id, total_keyframes=total_keyframes)
            return
            
        # Mark this job as having sent the completion event
        self._completion_events_sent.add(completion_key)
        
        await self.broker.publish_event("video.keyframes.masked.batch", event_data)
        logger.info(f"Emitted videos keyframes masked batch event",
                   job_id=job_id, event_id=event_id, total_keyframes=total_keyframes)

    async def publish_videos_keyframes_ready_batch(self, job_id: str, total_keyframes: int) -> None:
        """Publish videos keyframes ready batch completion event.
        
        Args:
            job_id: Job identifier
            total_keyframes: Total number of keyframes processed
        """
        event_id = str(uuid.uuid4())
        event_data = {
            "event_id": event_id,
            "job_id": job_id,
            "total_keyframes": total_keyframes
        }
        
        # Check if this job has already emitted a completion event for videos keyframes ready
        completion_key = f"{job_id}:video.keyframes.ready.batch"
        if completion_key in self._completion_events_sent:
            logger.info("Videos keyframes ready batch event already sent, skipping duplicate",
                       job_id=job_id, total_keyframes=total_keyframes)
            return
            
        # Mark this job as having sent the completion event
        self._completion_events_sent.add(completion_key)
        
        await self.broker.publish_event("videos.keyframes.ready.batch", event_data)
        logger.info(f"Emitted videos keyframes ready batch event",
                   job_id=job_id, event_id=event_id, total_keyframes=total_keyframes)
