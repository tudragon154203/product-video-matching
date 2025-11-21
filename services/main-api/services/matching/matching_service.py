from datetime import datetime, timezone
from typing import Optional
from common_py.database import DatabaseManager
from models.matching_schemas import MatchingSummaryResponse
from common_py.logging_config import configure_logging

logger = configure_logging("main-api:matching_service")


class MatchingService:
    """Service for matching phase operations"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def get_matching_summary(
        self,
        job_id: str,
        force_refresh: bool = False
    ) -> Optional[MatchingSummaryResponse]:
        """
        Get matching phase summary for a job.
        
        Args:
            job_id: Job ID
            force_refresh: Force refresh from database
            
        Returns:
            MatchingSummaryResponse or None if job not found
        """
        try:
            # Query job status
            job_query = """
                SELECT job_id, phase, created_at, updated_at
                FROM jobs
                WHERE job_id = $1
            """
            job = await self.db.fetch_one(job_query, job_id)
            
            if not job:
                return None
            
            # Determine status based on phase
            phase = job['phase']
            if phase == 'matching':
                status = 'running'
            elif phase in ('evidence', 'completed'):
                status = 'completed'
            elif phase == 'failed':
                status = 'failed'
            else:
                status = 'pending'
            
            # Query match statistics
            matches_count_query = """
                SELECT COUNT(*) as count
                FROM matches
                WHERE job_id = $1
            """
            matches_result = await self.db.fetch_one(
                matches_count_query, job_id
            )
            matches_found = matches_result['count'] if matches_result else 0
            
            # Matches with evidence
            evidence_count_query = """
                SELECT COUNT(*) as count
                FROM matches
                WHERE job_id = $1 AND evidence_path IS NOT NULL
            """
            evidence_result = await self.db.fetch_one(
                evidence_count_query, job_id
            )
            matches_with_evidence = (
                evidence_result['count'] if evidence_result else 0
            )
            
            # Average and P90 scores
            avg_score = None
            p90_score = None
            
            if matches_found > 0:
                scores_query = """
                    SELECT 
                        AVG(score) as avg_score,
                        PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY score) as p90_score
                    FROM matches
                    WHERE job_id = $1
                """
                scores_result = await self.db.fetch_one(scores_query, job_id)
                if scores_result:
                    avg_score = scores_result['avg_score']
                    p90_score = scores_result['p90_score']
            
            # Get product and video counts for candidates calculation
            product_images_query = """
                SELECT COUNT(DISTINCT pi.img_id) as count
                FROM product_images pi
                JOIN products p ON pi.product_id = p.product_id
                WHERE p.job_id = $1
            """
            product_result = await self.db.fetch_one(
                product_images_query, job_id
            )
            product_images_count = (
                product_result['count'] if product_result else 0
            )
            
            video_frames_query = """
                SELECT COUNT(DISTINCT vf.frame_id) as count
                FROM video_frames vf
                JOIN job_videos jv ON vf.video_id = jv.video_id
                WHERE jv.job_id = $1
            """
            video_result = await self.db.fetch_one(
                video_frames_query, job_id
            )
            video_frames_count = (
                video_result['count'] if video_result else 0
            )
            
            # Candidates total is product_images * video_frames
            candidates_total = product_images_count * video_frames_count
            
            # Estimate processed based on matches or phase progress
            candidates_processed = 0
            if status == 'completed':
                candidates_processed = candidates_total
            elif status == 'running' and candidates_total > 0:
                # Estimate based on matches found (rough approximation)
                # Assume we've processed enough to find the matches we have
                if matches_found > 0:
                    candidates_processed = min(
                        matches_found * 100,  # Rough estimate
                        candidates_total
                    )
                else:
                    # If no matches yet, assume we're early in processing
                    candidates_processed = int(candidates_total * 0.1)
            
            # Last event time (use job updated_at as proxy)
            last_event_at = job['updated_at']
            
            # Calculate ETA if running
            eta_seconds = None
            if status == 'running' and candidates_processed > 0:
                created_at = job['created_at']
                if created_at and last_event_at:
                    elapsed = (
                        last_event_at - created_at
                    ).total_seconds()
                    if elapsed > 0 and candidates_processed > 0:
                        rate = candidates_processed / elapsed
                        remaining = candidates_total - candidates_processed
                        if rate > 0:
                            eta_seconds = int(remaining / rate)
            
            return MatchingSummaryResponse(
                job_id=job_id,
                status=status,
                started_at=job['created_at'],
                completed_at=(
                    job['updated_at'] if status == 'completed' else None
                ),
                last_event_at=last_event_at,
                candidates_total=candidates_total,
                candidates_processed=candidates_processed,
                vector_pass_total=candidates_total,
                vector_pass_done=candidates_processed,
                ransac_checked=matches_found,
                matches_found=matches_found,
                matches_with_evidence=matches_with_evidence,
                avg_score=round(avg_score, 2) if avg_score else None,
                p90_score=round(p90_score, 2) if p90_score else None,
                queue_depth=0,
                eta_seconds=eta_seconds,
                blockers=[]
            )
            
        except Exception as e:
            logger.error(
                f"Error getting matching summary for job {job_id}: {e}"
            )
            raise
