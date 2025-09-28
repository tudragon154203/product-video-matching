"""Publish evidence generation completion events."""

import uuid
from typing import Any, Dict

from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging
from common_py.messaging import MessageBroker

logger = configure_logging("evidence-builder:evidence_publisher")


class EvidencePublisher:
    """Track job completion and emit evidence events."""

    def __init__(self, broker: MessageBroker, db: DatabaseManager) -> None:
        self.broker = broker
        self.db = db
        self.processed_jobs: set[str] = set()

    async def publish_evidence_completion_if_needed(self, job_id: str) -> None:
        if job_id in self.processed_jobs:
            return

        self.processed_jobs.add(job_id)
        evidences_completed_event = {
            "job_id": job_id,
            "event_id": str(uuid.uuid4()),
        }
        await self.broker.publish_event(
            "evidences.generation.completed",
            evidences_completed_event,
            correlation_id=job_id,
        )
        logger.info(
            "Published evidences.generation.completed",
            job_id=job_id,
            event_id=evidences_completed_event["event_id"],
        )

    async def check_and_complete_zero_matches_job(self, job_id: str) -> None:
        logger.info(
            "No matches found, completing evidence generation immediately",
            job_id=job_id,
        )
        await self.publish_evidence_completion_if_needed(job_id)

    async def handle_matchings_completed(
        self,
        event_data: Dict[str, Any],
    ) -> None:
        """Handle matchings completion events, covering zero-match cases."""
        job_id = event_data.get("job_id")
        if not job_id:
            raise ValueError("matchings.completed event is missing job_id")

        logger.info(
            "Checking job for matches after matching completed",
            job_id=job_id,
        )

        match_count = await self.db.fetch_val(
            "SELECT COUNT(*) FROM matches WHERE job_id = $1",
            job_id,
        ) or 0

        logger.info(
            "Match count for job",
            job_id=job_id,
            match_count=match_count,
        )

        if match_count == 0:
            await self.check_and_complete_zero_matches_job(job_id)
        else:
            logger.info(
                "Job has matches, evidence will be generated via match.result events",
                job_id=job_id,
                match_count=match_count,
            )
