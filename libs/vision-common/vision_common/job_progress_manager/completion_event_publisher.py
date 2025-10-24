import asyncio
import uuid
from typing import Dict, Any, Set, Optional, Tuple
from common_py.logging_config import configure_logging
from common_py.messaging import MessageBroker

logger = configure_logging("vision-common:completion_event_publisher")

class CompletionEventPublisher:
    # Constants
    DEFAULT_WATERMARK_TTL = 300
    FAILED_ASSETS_PLACEHOLDER = 0
    
    def __init__(self, broker: MessageBroker, base_manager):
        self.broker = broker
        self.base_manager = base_manager
        self._completion_events_sent: set = set()  # Track completion events sent to prevent duplicates

    def _create_completion_key(self, job_id: str, asset_type: str, event_type: str) -> str:
        """Generate a unique completion key for job and event type"""
        return f"{job_id}:{asset_type}:{event_type}"

    def _is_duplicate_event(self, completion_key: str) -> bool:
        """Check if completion event has already been sent"""
        is_duplicate = completion_key in self._completion_events_sent
        if is_duplicate:
            logger.warning("DUPLICATE COMPLETION EVENT DETECTED - skipping",
                         completion_key=completion_key, current_set_size=len(self._completion_events_sent))
        return is_duplicate

    def _mark_event_sent(self, completion_key: str) -> None:
        """Mark completion event as sent and log it"""
        self._completion_events_sent.add(completion_key)
        logger.debug("Marked completion event as sent",
                    completion_key=completion_key, total_set_size=len(self._completion_events_sent))

    def _prepare_completion_event_data(self, job_id: str, expected: int, done: int, 
                                     has_partial: bool, is_timeout: bool = False) -> Dict[str, Any]:
        """Prepare standard completion event data"""
        event_id = str(uuid.uuid4())
        return {
            "job_id": job_id,
            "event_id": event_id,
            "total_assets": expected,
            "processed_assets": done,
            "failed_assets": self.FAILED_ASSETS_PLACEHOLDER,
            "has_partial_completion": has_partial or is_timeout,
            "watermark_ttl": self.DEFAULT_WATERMARK_TTL,
            "idempotent": True
        }

    def _determine_event_type(self, asset_type: str, event_type_prefix: str) -> str:
        """Determine the event type based on asset type and prefix"""
        if event_type_prefix == "segmentation":
            return f"{asset_type}.masked.batch" if asset_type in ["products", "video"] else f"{asset_type}.{event_type_prefix}.completed"
        return f"image.{event_type_prefix}.completed" if asset_type == "image" else f"video.{event_type_prefix}.completed"

    async def _publish_event(self, event_type: str, event_data: Dict[str, Any], 
                           completion_key: str, message: str) -> None:
        """Publish event with standardized logging and error handling"""
        await self.broker.publish_event(topic=event_type, event_data=event_data)
        logger.info(message, job_id=event_data["job_id"], event_id=event_data["event_id"],
                   total=event_data["total_assets"], done=event_data["processed_assets"])

    def _handle_zero_asset_case(self, expected: int) -> Tuple[int, bool]:
        """Handle zero asset edge case"""
        if expected == 0:
            return 0, False  # done=0, has_partial=False
        return expected, (expected > 0)  # Return expected and whether it's partial

    async def publish_completion_event(self, job_id: str, is_timeout: bool = False, event_type_prefix: str = "embeddings"):
        """Publish completion event with progress data"""
        # Find tracking entry by (job_id, *, event_type_prefix)
        job_key = None
        for key in self.base_manager.job_tracking.keys():
            if key.startswith(f"{job_id}:") and key.endswith(f":{event_type_prefix}"):
                job_key = key
                break
        if not job_key:
            logger.warning("Job not found in tracking for completion publish", job_id=job_id, event_type_prefix=event_type_prefix)
            return
        job_data = self.base_manager.job_tracking[job_key]
        # key format: job_id:asset_type:event_type_prefix
        try:
            _, asset_type, _ = job_key.split(":", 2)
        except Exception:
            asset_type = job_data.get("asset_type", "image")
        expected = job_data["expected"]
        done = job_data["done"]
        
        # Handle zero assets scenario - but only if this is a legitimate zero-asset job
        # (not per-asset-first initialization where expected hasn't been set yet)
        if expected == 0:
            # Check if this is a legitimate zero-asset job by seeing if batch was initialized
            # If batch was initialized and total is 0, it's a real zero-asset job
            is_legitimate_zero = False
            if asset_type == "image" and job_id in self.base_manager.job_image_counts:
                if self.base_manager.job_image_counts[job_id].get("total", 0) == 0:
                    is_legitimate_zero = True
            elif asset_type == "video" and job_id in self.base_manager.job_frame_counts:
                if self.base_manager.job_frame_counts[job_id].get("total", 0) == 0:
                    is_legitimate_zero = True

            if is_legitimate_zero:
                done = 0
                logger.info("Immediate completion for legitimate zero-asset job", job_id=job_id)
                has_partial = False  # For zero assets, there's no partial completion
            else:
                # This is likely per-asset-first initialization, don't complete yet
                logger.debug("Skipping completion - zero expected but not a legitimate zero-asset job",
                           job_id=job_id, asset_type=asset_type)
                return
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
        
        await self.broker.publish_event(topic=event_type, event_data=event_data)
        logger.info(f"Emitted {asset_type} {event_type_prefix} completed event",
                   job_id=job_id, event_id=event_id,
                   total=expected, done=done, is_timeout=is_timeout)
        
        # Cleanup handled by JobProgressManager to also cancel timers; do not cleanup here

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
            logger.warning("DUPLICATE COMPLETION EVENT DETECTED - skipping",
                          job_id=job_id, asset_type=asset_type, event_type_prefix=event_type_prefix,
                          completion_key=completion_key, current_set_size=len(self._completion_events_sent))
            return
            
        # Mark this job and asset_type as having sent completion event
        self._completion_events_sent.add(completion_key)
        logger.debug("Added completion key to set", job_id=job_id, asset_type=asset_type,
                     current_set_size=len(self._completion_events_sent))
        
        await self.broker.publish_event(topic=event_type, event_data=event_data)
        logger.info(f"Emitted {asset_type} {event_type_prefix} completed event",
                   job_id=job_id, event_id=event_id,
                   total=expected, done=done, is_timeout=False)
        
        # Cleanup handled by JobProgressManager to also cancel timers; do not cleanup here
        
        # For segmentation completion, emit masked batch events if this is a segmentation job
        if event_type_prefix == "segmentation":
            await self.emit_segmentation_masked_batch_events(job_id, asset_type, expected, done)

    async def emit_segmentation_masked_batch_events(self, job_id: str, asset_type: str, expected: int, done: int):
        """Emit masked batch events when segmentation completes"""
        if asset_type == "image":
            await self.publish_products_images_masked_batch(job_id, done)
        elif asset_type == "video":
            await self.publish_videos_keyframes_masked_batch(job_id, done)

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
        
        await self.broker.publish_event(topic="products.images.masked.batch", event_data=event_data)
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
        
        await self.broker.publish_event(topic="video.keyframes.masked.batch", event_data=event_data)
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
        
        await self.broker.publish_event(topic="videos.keyframes.ready.batch", event_data=event_data)
        logger.info(f"Emitted videos keyframes ready batch event",
                   job_id=job_id, event_id=event_id, total_keyframes=total_keyframes)
