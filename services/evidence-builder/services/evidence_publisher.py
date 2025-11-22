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

    async def has_published_completion(self, job_id: str) -> bool:
        """Check if completion event has already been published for this job."""
        query = """
            SELECT EXISTS(
                SELECT 1 FROM processed_events
                WHERE event_type = 'evidences_generation_completed'
                AND dedup_key = $1
            )
        """
        result = await self.db.fetch_val(query, job_id)
        return bool(result)

    async def mark_completion_published(self, job_id: str) -> None:
        """Mark completion event as published for idempotency."""
        event_id = str(uuid.uuid4())
        query = """
            INSERT INTO processed_events (event_id, event_type, dedup_key, processed_at)
            VALUES ($1, 'evidences_generation_completed', $2, NOW())
            ON CONFLICT (event_type, dedup_key) DO NOTHING
        """
        await self.db.execute(query, event_id, job_id)

    async def check_and_publish_completion(self, job_id: str) -> None:
        """Check if all evidence is ready and publish completion if so."""
        if await self.has_published_completion(job_id):
            logger.debug(
                "Completion already published for job",
                job_id=job_id,
            )
            return

        # Get match counts
        total_query = "SELECT COUNT(*) FROM matches WHERE job_id = $1"
        evidence_query = """
            SELECT COUNT(*) FROM matches
            WHERE job_id = $1 AND evidence_path IS NOT NULL
        """
        total_matches = await self.db.fetch_val(total_query, job_id) or 0
        matches_with_evidence = await self.db.fetch_val(evidence_query, job_id) or 0

        logger.info(
            "Checking evidence completion status",
            job_id=job_id,
            total_matches=total_matches,
            matches_with_evidence=matches_with_evidence,
        )

        # Only publish if all matches have evidence
        if total_matches > 0 and matches_with_evidence >= total_matches:
            await self._publish_completion(job_id)

    async def _publish_completion(self, job_id: str) -> None:
        """Publish evidences.generation.completed event."""
        evidences_completed_event = {
            "job_id": job_id,
            "event_id": str(uuid.uuid4()),
        }
        await self.broker.publish_event(
            "evidences.generation.completed",
            evidences_completed_event,
            correlation_id=job_id,
        )
        await self.mark_completion_published(job_id)
        logger.info(
            "Published evidences.generation.completed",
            job_id=job_id,
            event_id=evidences_completed_event["event_id"],
        )

    async def handle_match_request_completed(
        self,
        event_data: Dict[str, Any],
        correlation_id: str,
    ) -> None:
        """Handle match.request.completed events, covering zero-match cases."""
        job_id = event_data.get("job_id")
        if not job_id:
            raise ValueError("match.request.completed event is missing job_id")

        logger.info(
            "Checking job for matches after matching completed",
            job_id=job_id,
            correlation_id=correlation_id,
        )

        match_count = await self.db.fetch_val(
            "SELECT COUNT(*) FROM matches WHERE job_id = $1",
            job_id,
        ) or 0

        logger.info(
            "Match count for job",
            job_id=job_id,
            match_count=match_count,
            correlation_id=correlation_id,
        )

        # For zero-match jobs, publish completion immediately
        if match_count == 0:
            if not await self.has_published_completion(job_id):
                logger.info(
                    "No matches found, completing evidence generation immediately",
                    job_id=job_id,
                    correlation_id=correlation_id,
                )
                await self._publish_completion(job_id)
        else:
            logger.info(
                "Job has matches, evidence will be generated via match.result events",
                job_id=job_id,
                match_count=match_count,
                correlation_id=correlation_id,
            )
