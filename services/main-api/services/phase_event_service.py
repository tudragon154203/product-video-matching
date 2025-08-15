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
        std_logger.info(f"Received event: {event_type} for job {event_data.get('job_id')}")
        
        # Validate event
        try:
            validator.validate_event(event_type, event_data)
            std_logger.info(f"Event validation passed: {event_type}")
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
        std_logger.info(f"Added event to processed cache: {event_id}")
        
        # Store event in database
        try:
            await self.db_handler.store_phase_event(event_id, job_id, event_type)
            std_logger.info(f"Stored phase event: {event_type} for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to store phase event {event_id} for job {job_id}: {str(e)}")
            # Remove from cache if storage failed
            self.processed_events.discard(event_id)
            std_logger.error(f"Removed event from cache due to storage failure: {event_id}")
            return
            
        std_logger.info(f"Stored phase event for job {job_id}: {event_type} (event_id={event_id})")
        
        # Check if we need to trigger a phase transition
        await self.check_phase_transitions(job_id, event_type)
        
    async def check_phase_transitions(self, job_id: str, event_type: str):
        """Check if we need to transition to a new phase based on job-based completion events"""
        try:
            current_phase = await self.db_handler.get_job_phase(job_id)
            logger.info(f"Checking phase transitions for job {job_id}: current_phase={current_phase}, event_type={event_type}")
            
            if current_phase == "collection":
                # For now, assume collection phase transitions to feature_extraction automatically
                # In a real implementation, this would be triggered by collection completion events
                logger.info(f"Transitioning from collection to feature_extraction for job {job_id}")
                await self.db_handler.update_job_phase(job_id, "feature_extraction")
                    
            elif current_phase == "feature_extraction":
                # Get job type to determine required events
                try:
                    job_type = await self.db_handler.get_job_asset_types(job_id)
                    std_logger.info(f"Job {job_id} asset_types: {job_type}")
                except Exception as e:
                    logger.error(f"Failed to get asset types for job {job_id}: {str(e)}")
                    return
                
                # Check required events based on job type
                required_events = []
                if job_type.get("images", False):
                    required_events.append("image.embeddings.completed")
                    required_events.append("image.keypoints.completed")
                if job_type.get("videos", False):
                    required_events.append("video.embeddings.completed")
                    required_events.append("video.keypoints.completed")
                
                std_logger.info(f"Job {job_id} requires events: {required_events}")
                
                # Verify all required events are completed
                all_events_received = True
                missing_events = []
                for event in required_events:
                    try:
                        if not await self.db_handler.has_phase_event(job_id, event):
                            all_events_received = False
                            missing_events.append(event)
                    except Exception as e:
                        logger.error(f"Database error checking event {event} for job {job_id}: {str(e)}")
                        all_events_received = False
                
                if all_events_received:
                    logger.info(f"All feature extraction completed, transitioning to matching for job {job_id}")
                    await self.db_handler.update_job_phase(job_id, "matching")
                    
                    # Publish match request
                    await self._publish_match_request_for_job(job_id)
                else:
                    std_logger.warning(f"Job {job_id} missing required events: {missing_events}")
                        
            elif current_phase == "matching":
                # Check for matching completion event
                if event_type == "matchings.process.completed":
                    logger.info(f"Matching completed, transitioning to evidence for job {job_id}")
                    await self.db_handler.update_job_phase(job_id, "evidence")
                else:
                    # If job is in matching phase but we received a feature extraction event,
                    # it might mean the job was manually moved to matching without publishing match request
                    # This is a safety net to ensure match requests are published
                    logger.info(f"Job {job_id} is in matching phase, ensuring match request is published")
                    await self._publish_match_request_for_job(job_id)
                    
            elif current_phase == "evidence":
                # Check for evidence completion event
                if event_type == "evidences.generation.completed":
                    logger.info(f"Evidence generation completed, transitioning to completed for job {job_id}")
                    try:
                        await self.db_handler.update_job_phase(job_id, "completed")
                        logger.info(f"Successfully updated job {job_id} phase to completed")
                        
                        # Publish job completion event
                        await self.broker_handler.publish_job_completed(job_id)
                        logger.info(f"Published job completion event for job {job_id}")
                    except Exception as e:
                        logger.error(f"Failed to complete job {job_id}: {str(e)}")
                        raise
                else:
                    # Log when evidence phase receives other events
                    logger.info(f"Job {job_id} in evidence phase received {event_type} event (no action needed)")
            
            # Handle evidences.generation.completed regardless of current phase to avoid race conditions
            if event_type == "evidences.generation.completed" and current_phase != "evidence":
                logger.info(f"Evidence generation completed but job {job_id} is in {current_phase} phase, checking if we should transition")
                
                # Check if job should be in evidence phase (i.e., matching is complete)
                if await self.db_handler.has_phase_event(job_id, "matchings.process.completed"):
                    logger.info(f"Matching is complete, transitioning job {job_id} to evidence then completed")
                    try:
                        # First transition to evidence phase if not already there
                        if current_phase != "evidence":
                            await self.db_handler.update_job_phase(job_id, "evidence")
                            logger.info(f"Updated job {job_id} phase to evidence")
                        
                        # Then transition to completed
                        await self.db_handler.update_job_phase(job_id, "completed")
                        logger.info(f"Successfully updated job {job_id} phase to completed")
                        
                        # Publish job completion event
                        await self.broker_handler.publish_job_completed(job_id)
                        logger.info(f"Published job completion event for job {job_id}")
                    except Exception as e:
                        logger.error(f"Failed to complete job {job_id}: {str(e)}")
                        raise
                else:
                    logger.warning(f"Evidence generation completed for job {job_id} but matching is not complete yet")
                    
        except Exception as e:
            logger.error(f"Failed to check phase transitions for job {job_id}: {str(e)}")
    
    async def _publish_match_request_for_job(self, job_id: str):
        """Helper method to publish match request for a job"""
        try:
            industry = await self.db_handler.get_job_industry(job_id)
            await self.broker_handler.publish_match_request(
                job_id,
                industry,
                job_id,  # product_set_id
                job_id   # video_set_id
            )
            logger.info(f"Published match request for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to publish match request for job {job_id}: {str(e)}")