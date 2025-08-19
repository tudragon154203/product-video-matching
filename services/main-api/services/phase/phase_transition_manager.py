import asyncio
import logging
from typing import Dict, Any, List
from common_py.logging_config import configure_logging
from handlers.database_handler import DatabaseHandler
from handlers.broker_handler import BrokerHandler

logger = configure_logging("main-api")

class PhaseTransitionManager:
    def __init__(self, db_handler: DatabaseHandler, broker_handler: BrokerHandler):
        self.db_handler = db_handler
        self.broker_handler = broker_handler

    async def check_phase_transitions(self, job_id: str, event_type: str):
        """Check if we need to transition to a new phase based on job-based completion events"""
        try:
            current_phase = await self.db_handler.get_job_phase(job_id)
            logger.info(f"Checking phase transitions for job {job_id}: current_phase={current_phase}, event_type={event_type}")
            
            if current_phase == "collection":
                await self._process_collection_phase(job_id)
                    
            elif current_phase == "feature_extraction":
                await self._process_feature_extraction_phase(job_id)
                        
            elif current_phase == "matching":
                await self._process_matching_phase(job_id, event_type)
                    
            elif current_phase == "evidence":
                await self._process_evidence_phase(job_id, event_type)
            
            await self._handle_cross_phase_evidence_completion(job_id, event_type, current_phase)
                    
        except Exception as e:
            logger.error(f"Failed to check phase transitions for job {job_id}: {str(e)}")
    
    async def _process_collection_phase(self, job_id: str):
        logger.info(f"Transitioning from collection to feature_extraction for job {job_id}")
        await self.db_handler.update_job_phase(job_id, "feature_extraction")

    async def _process_feature_extraction_phase(self, job_id: str):
        try:
            job_type = await self.db_handler.get_job_asset_types(job_id)
            logger.info(f"Job {job_id} asset_types: {job_type}")
        except Exception as e:
            logger.error(f"Failed to get asset types for job {job_id}: {str(e)}")
            return
        
        required_events = self._get_required_feature_events(job_type)
        logger.info(f"Job {job_id} requires events: {required_events}")
        
        if not required_events:
            logger.info(f"Zero-asset job {job_id} detected, transitioning directly from feature_extraction to matching")
            await self.db_handler.update_job_phase(job_id, "matching")
            await self._publish_match_request_for_job(job_id)
            return
        
        all_events_received, missing_events = await self._check_all_feature_events_received(job_id, required_events)
        
        if all_events_received:
            logger.info(f"All required feature extraction completed, transitioning to matching for job {job_id}")
            await self.db_handler.update_job_phase(job_id, "matching")
            await self._publish_match_request_for_job(job_id)
        else:
            logger.info(f"Job {job_id} waiting for required events: {missing_events}")

    def _get_required_feature_events(self, job_type: Dict[str, bool]) -> List[str]:
        required_events = []
        if job_type.get("images", False):
            required_events.append("image.embeddings.completed")
            required_events.append("image.keypoints.completed")
        if job_type.get("videos", False):
            required_events.append("video.embeddings.completed")
            required_events.append("video.keypoints.completed")
        return required_events

    async def _check_all_feature_events_received(self, job_id: str, required_events: List[str]) -> tuple[bool, List[str]]:
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
        return all_events_received, missing_events

    async def _process_matching_phase(self, job_id: str, event_type: str):
        if event_type == "matchings.process.completed":
            logger.info(f"Matching completed, transitioning to evidence for job {job_id}")
            await self.db_handler.update_job_phase(job_id, "evidence")
        else:
            logger.info(f"Job {job_id} is in matching phase, ensuring match request is published")
            await self._publish_match_request_for_job(job_id)

    async def _process_evidence_phase(self, job_id: str, event_type: str):
        if event_type == "evidences.generation.completed":
            logger.info(f"Evidence generation completed, transitioning to completed for job {job_id}")
            try:
                await self.db_handler.update_job_phase(job_id, "completed")
                logger.info(f"Successfully updated job {job_id} phase to completed")
                await self.broker_handler.publish_job_completed(job_id)
                logger.info(f"Published job completion event for job {job_id}")
            except Exception as e:
                logger.error(f"Failed to complete job {job_id}: {str(e)}")
                raise
        else:
            logger.info(f"Job {job_id} in evidence phase received {event_type} event (no action needed)")

    async def _handle_cross_phase_evidence_completion(self, job_id: str, event_type: str, current_phase: str):
        if event_type == "evidences.generation.completed" and current_phase != "evidence":
            logger.info(f"Evidence generation completed but job {job_id} is in {current_phase} phase, checking if we should transition")
            
            if await self.db_handler.has_phase_event(job_id, "matchings.process.completed"):
                logger.info(f"Matching is complete, transitioning job {job_id} to evidence then completed")
                try:
                    if current_phase != "evidence":
                        await self.db_handler.update_job_phase(job_id, "evidence")
                        logger.info(f"Updated job {job_id} phase to evidence")
                    
                    await self.db_handler.update_job_phase(job_id, "completed")
                    logger.info(f"Successfully updated job {job_id} phase to completed")
                    
                    await self.broker_handler.publish_job_completed(job_id)
                    logger.info(f"Published job completion event for job {job_id}")
                except Exception as e:
                    logger.error(f"Failed to complete job {job_id}: {str(e)}")
                    raise
            else:
                logger.warning(f"Evidence generation completed for job {job_id} but matching is not complete yet")
    
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
