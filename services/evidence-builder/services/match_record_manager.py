"""Database helpers for evidence builder match records."""

from typing import Any, Optional

from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging

logger = configure_logging("evidence-builder:match_record_manager")


class MatchRecordManager:
    """Fetch and update match-related persistence."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    async def is_evidence_processed(self, dedup_key: str) -> bool:
        """Check if evidence has already been processed for this match."""
        query = """
            SELECT EXISTS(
                SELECT 1 FROM processed_events
                WHERE event_type = 'evidence_generated'
                AND dedup_key = $1
            )
        """
        result = await self.db.fetch_val(query, dedup_key)
        return bool(result)

    async def mark_evidence_processed(self, dedup_key: str) -> None:
        """Mark evidence as processed for idempotency."""
        query = """
            INSERT INTO processed_events (event_type, dedup_key, processed_at)
            VALUES ('evidence_generated', $1, NOW())
            ON CONFLICT (event_type, dedup_key) DO NOTHING
        """
        await self.db.execute(query, dedup_key)

    async def update_match_record_and_log(
        self,
        job_id: str,
        product_id: str,
        video_id: str,
        evidence_path: str,
    ) -> None:
        await self.db.execute(
            (
                "UPDATE matches SET evidence_path = $1 "
                "WHERE product_id = $2 AND video_id = $3 AND job_id = $4"
            ),
            evidence_path,
            product_id,
            video_id,
            job_id,
        )
        logger.info(
            "Generated evidence",
            job_id=job_id,
            product_id=product_id,
            video_id=video_id,
            evidence_path=evidence_path,
        )

    async def get_image_info(self, img_id: str) -> Optional[dict[str, Any]]:
        """Get product image information."""
        query = (
            "SELECT local_path, kp_blob_path FROM product_images WHERE img_id = $1"
        )
        return await self.db.fetch_one(query, img_id)

    async def get_frame_info(self, frame_id: str) -> Optional[dict[str, Any]]:
        """Get video frame information."""
        query = (
            "SELECT local_path, kp_blob_path FROM video_frames WHERE frame_id = $1"
        )
        return await self.db.fetch_one(query, frame_id)

    async def get_match_counts(self, job_id: str) -> tuple[int, int]:
        """Get total matches and evidence-ready matches for a job."""
        total_query = "SELECT COUNT(*) FROM matches WHERE job_id = $1"
        evidence_query = """
            SELECT COUNT(*) FROM matches
            WHERE job_id = $1 AND evidence_path IS NOT NULL
        """
        total = await self.db.fetch_val(total_query, job_id) or 0
        with_evidence = await self.db.fetch_val(evidence_query, job_id) or 0
        return total, with_evidence
