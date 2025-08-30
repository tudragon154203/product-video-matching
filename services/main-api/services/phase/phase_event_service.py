import asyncio
import uuid
from typing import Dict, Any, Set
from common_py.logging_config import configure_logging
from handlers.database_handler import DatabaseHandler
from handlers.broker_handler import BrokerHandler
from contracts.validator import validator
from .phase_transition_manager import PhaseTransitionManager

logger = configure_logging("main-api")


class PhaseEventService:
    def __init__(self, db_handler: DatabaseHandler, broker_handler: BrokerHandler):
        self.db_handler = db_handler
        self.broker_handler = broker_handler
        self.processed_events: Set[str] = set()  # In-memory deduplication cache
        self.phase_transition_manager = PhaseTransitionManager(db_handler, broker_handler)
        
    async def handle_phase_event(self, event_type: str, event_data: Dict[str, Any]):
        """Handle a job-based completion event"""
        logger.info(f"Received event: {event_type} for job {event_data.get('job_id')}")
        
        event_id = event_data.get("event_id")
        job_id = event_data.get("job_id")
        
        if not event_id or not job_id:
            logger.error(f"Missing event_id or job_id in event: {event_type}")
            return
        
        if event_id in self.processed_events:
            logger.info(f"Duplicate event, skipping: {event_id} for job {job_id}")
            return
            
        try:
            validator.validate_event(event_type, event_data)
            logger.info(f"Event validation passed: {event_type}")
        except ValueError as e:
            if "Unknown event type" in str(e):
                logger.error(f"Unknown event type received: {event_type}. Available schemas: {list(validator.schemas.keys())}")
            else:
                logger.error(f"Event validation failed for {event_type}: {str(e)}")
            return
        except Exception as e:
            logger.error(f"Event validation failed for {event_type}: {str(e)}")
            return
            
        has_partial_completion = event_data.get("has_partial_completion", False)
        if has_partial_completion:
            logger.warning(f"Job completed with partial results for job {job_id} ({event_type})")
            
        self.processed_events.add(event_id)
        logger.info(f"Added event to processed cache: {event_id}")
        
        # Store event in database
        try:
            await self.db_handler.store_phase_event(event_id, job_id, event_type)
            logger.info(f"Stored phase event: {event_type} for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to store phase event: {str(e)}")
            self.processed_events.discard(event_id)
            logger.error(f"Removed event from cache due to storage failure: {event_id}")
            return
            
        logger.info(f"Stored phase event for job {job_id}: {event_type} (event_id={event_id})")
        
        await self.phase_transition_manager.check_phase_transitions(job_id, event_type)