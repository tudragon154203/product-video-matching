import uuid
from typing import Dict, Any, Set
from common_py.messaging import MessageBroker
from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging

logger = configure_logging("evidence-builder")

class EvidencePublisher:
    def __init__(self, broker: MessageBroker, db: DatabaseManager):
        self.broker = broker
        self.db = db
        self.processed_jobs = set() # Track processed jobs to ensure we only publish evidences.generation.completed once per job

    async def publish_evidence_completion_if_needed(self, job_id: str):
        if job_id not in self.processed_jobs:
            self.processed_jobs.add(job_id)
            evidences_completed_event = {
                "job_id": job_id,
                "event_id": str(uuid.uuid4())
            }
            await self.broker.publish_event(
                "evidences.generation.completed",
                evidences_completed_event,
                correlation_id=job_id
            )
            logger.info("Published evidences.generation.completed", 
                       job_id=job_id,
                       event_id=evidences_completed_event["event_id"])

    async def check_and_complete_zero_matches_job(self, job_id: str):
        logger.info("No matches found, completing evidence generation immediately", job_id=job_id)
        await self.publish_evidence_completion_if_needed(job_id)

    async def handle_matchings_completed(self, event_data: Dict[str, Any]):
        """Handle matchings process completed event - check if job has matches and complete if none"""
        try:
            job_id = event_data["job_id"]
            
            logger.info("Checking job for matches after matching completed", job_id=job_id)
            
            match_count = await self.db.fetch_val(
                "SELECT COUNT(*) FROM matches WHERE job_id = $1", job_id
            ) or 0
            
            logger.info("Match count for job", job_id=job_id, match_count=match_count)
            
            if match_count == 0:
                await self.check_and_complete_zero_matches_job(job_id)
            else:
                logger.info("Job has matches, evidence will be generated via match.result events", 
                           job_id=job_id, match_count=match_count)
            
        except Exception as e:
            logger.error("Failed to handle matchings completed", error=str(e))
            raise
