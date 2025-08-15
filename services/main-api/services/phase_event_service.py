import asyncio
import logging
import uuid
from typing import Dict, Any, Set
from common_py.logging_config import configure_logging
from handlers.database_handler import DatabaseHandler
from handlers.broker_handler import BrokerHandler
from contracts.validator import validator

logger = configure_logging("main-api")
# Also get a standard logger for test compatibility
std_logger = logging.getLogger("main-api")


class PhaseEventService:
    def __init__(self, db_handler: DatabaseHandler, broker_handler: BrokerHandler):
        self.db_handler = db_handler
        self.broker_handler = broker_handler
        self.processed_events: Set[str] = set()  # In-memory deduplication cache
        
    async def handle_phase_event(self, event_type: str, event_data: Dict[str, Any]):
        """Handle a job-based completion event"""
        # Validate event
        try:
            validator.validate_event(event_type, event_data)
        except ValueError as e:
            if "Unknown event type" in str(e):
                logger.error(f"Unknown event type received: {event_type}. Available schemas: {list(validator.schemas.keys())}")
            else:
                logger.error(f"Event validation failed for {event_type}: {str(e)}")
            return
        except Exception as e:
            logger.error(f"Event validation failed for {event_type}: {str(e)}")
            return
            
        event_id = event_data.get("event_id")
        job_id = event_data.get("job_id")
        
        if not event_id or not job_id:
            logger.error(f"Missing event_id or job_id in event: {event_type}")
            return
            
        # Handle partial completion flag for embedding events
        has_partial_completion = event_data.get("has_partial_completion", False)
        if has_partial_completion:
            logger.warning(f"Job completed with partial results for job {job_id} ({event_type})")
            
        # Deduplication - check if we've already processed this event
        if event_id in self.processed_events:
            std_logger.info(f"Duplicate event, skipping: {event_id} for job {job_id}")
            return
            
        # Add to processed events
        self.processed_events.add(event_id)
        
        # Store event in database
        try:
            await self.db_handler.store_phase_event(event_id, job_id, event_type)
        except Exception as e:
            logger.error(f"Failed to store phase event {event_id} for job {job_id}: {str(e)}")
            # Remove from cache if storage failed
            self.processed_events.discard(event_id)
            return
            
        std_logger.info(f"Stored phase event for job {job_id}: {event_type} (event_id={event_id})")
        
        # Check if we need to trigger a phase transition
        await self.check_phase_transitions(job_id, event_type)
        
    async def check_phase_transitions(self, job_id: str, event_type: str):
        """Check if we need to transition to a new phase based on job-based completion events"""
        try:
            current_phase = await self.db_handler.get_job_phase(job_id)
            
            if current_phase == "collection":
                # For now, assume collection phase transitions to feature_extraction automatically
                # In a real implementation, this would be triggered by collection completion events
                logger.info(f"Transitioning from collection to feature_extraction for job {job_id}")
                await self.db_handler.update_job_phase(job_id, "feature_extraction")
                    
            elif current_phase == "feature_extraction":
                # Get job type to determine required events
                job_type = await self.db_handler.get_job_asset_types(job_id)
                
                # Check required events based on job type
                required_events = []
                if job_type.get("images", False):
                    required_events.append("image.embeddings.completed")
                    required_events.append("image.keypoints.completed")
                if job_type.get("videos", False):
                    required_events.append("video.embeddings.completed")
                    required_events.append("video.keypoints.completed")
                
                # Verify all required events are completed
                all_events_received = True
                for event in required_events:
                    if not await self.db_handler.has_phase_event(job_id, event):
                        all_events_received = False
                        break
                
                if all_events_received:
                    logger.info(f"All feature extraction completed, transitioning to matching for job {job_id}")
                    await self.db_handler.update_job_phase(job_id, "matching")
                    
                    # Publish match request
                    try:
                        industry = await self.db_handler.get_job_industry(job_id)
                        await self.broker_handler.publish_match_request(
                            job_id,
                            industry,
                            job_id,  # product_set_id
                            job_id   # video_set_id
                        )
                    except Exception as e:
                        logger.error(f"Failed to publish match request for job {job_id}: {str(e)}")
                        
            elif current_phase == "matching":
                # For now, assume matching phase transitions to evidence automatically
                # In a real implementation, this would be triggered by matching completion events
                logger.info(f"Transitioning from matching to evidence for job {job_id}")
                await self.db_handler.update_job_phase(job_id, "evidence")
                    
            elif current_phase == "evidence":
                # For now, assume evidence phase transitions to completed automatically
                # In a real implementation, this would be triggered by evidence completion events
                logger.info(f"Transitioning from evidence to completed for job {job_id}")
                await self.db_handler.update_job_phase(job_id, "completed")
                
                # Publish job completion event
                try:
                    await self.broker_handler.publish_job_completed(job_id)
                except Exception as e:
                    logger.error(f"Failed to publish job completion for job {job_id}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Failed to check phase transitions for job {job_id}: {str(e)}")