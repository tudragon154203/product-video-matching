import asyncio
import logging
import uuid
from typing import Dict, Any, Set
from common_py.logging_config import configure_logging
from handlers.database_handler import DatabaseHandler
from handlers.broker_handler import BrokerHandler
from contracts.validator import validator

logger = configure_logging("main-api")


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
                logger.error("Unknown event type received", event_type=event_type, available_schemas=list(validator.schemas.keys()))
            else:
                logger.error("Event validation failed", event_type=event_type, error=str(e))
            return
        except Exception as e:
            logger.error("Event validation failed", event_type=event_type, error=str(e))
            return
            
        event_id = event_data.get("event_id")
        job_id = event_data.get("job_id")
        
        if not event_id or not job_id:
            logger.error("Missing event_id or job_id in event", event_type=event_type)
            return
            
        # Handle partial completion flag for embedding events
        has_partial_completion = event_data.get("has_partial_completion", False)
        if has_partial_completion:
            logger.warning("Job completed with partial results", job_id=job_id, event_type=event_type)
            
        # Deduplication - check if we've already processed this event
        if event_id in self.processed_events:
            logger.info("Duplicate event, skipping", event_id=event_id, event_type=event_type)
            return
            
        # Add to processed events
        self.processed_events.add(event_id)
        
        # Store event in database
        try:
            await self.db_handler.store_phase_event(event_id, job_id, event_type)
        except Exception as e:
            logger.error("Failed to store phase event", event_id=event_id, error=str(e))
            # Remove from cache if storage failed
            self.processed_events.discard(event_id)
            return
            
        logger.info("Stored phase event", event_id=event_id, job_id=job_id, event_type=event_type)
        
        # Check if we need to trigger a phase transition
        await self.check_phase_transitions(job_id, event_type)
        
    async def check_phase_transitions(self, job_id: str, event_type: str):
        """Check if we need to transition to a new phase based on job-based completion events"""
        try:
            current_phase = await self.db_handler.get_job_phase(job_id)
            
            if current_phase == "collection":
                # For now, assume collection phase transitions to feature_extraction automatically
                # In a real implementation, this would be triggered by collection completion events
                logger.info("Transitioning from collection to feature_extraction", job_id=job_id)
                await self.db_handler.update_job_phase(job_id, "feature_extraction")
                    
            elif current_phase == "feature_extraction":
                # Check if we have all four job-based completion events
                image_embeddings_completed = await self.db_handler.has_phase_event(job_id, "image.embeddings.completed")
                video_embeddings_completed = await self.db_handler.has_phase_event(job_id, "video.embeddings.completed")
                image_keypoints_completed = await self.db_handler.has_phase_event(job_id, "image.keypoints.completed")
                video_keypoints_completed = await self.db_handler.has_phase_event(job_id, "video.keypoints.completed")
                
                if (image_embeddings_completed and video_embeddings_completed and
                    image_keypoints_completed and video_keypoints_completed):
                    logger.info("All feature extraction completed, transitioning to matching", job_id=job_id)
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
                        logger.error("Failed to publish match request", job_id=job_id, error=str(e))
                        
            elif current_phase == "matching":
                # For now, assume matching phase transitions to evidence automatically
                # In a real implementation, this would be triggered by matching completion events
                logger.info("Transitioning from matching to evidence", job_id=job_id)
                await self.db_handler.update_job_phase(job_id, "evidence")
                    
            elif current_phase == "evidence":
                # For now, assume evidence phase transitions to completed automatically
                # In a real implementation, this would be triggered by evidence completion events
                logger.info("Transitioning from evidence to completed", job_id=job_id)
                await self.db_handler.update_job_phase(job_id, "completed")
                    
        except Exception as e:
            logger.error("Failed to check phase transitions", job_id=job_id, error=str(e))