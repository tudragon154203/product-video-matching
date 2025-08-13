from common_py.database import DatabaseManager
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DatabaseHandler:
    def __init__(self, db: DatabaseManager):
        self.db = db

    async def store_job(self, job_id: str, query: str, industry: str, queries: Dict[str, Any], phase: str):
        """Store a new job in the database."""
        try:
            await self.db.execute(
                "INSERT INTO jobs (job_id, query, industry, queries, phase) VALUES ($1, $2, $3, $4, $5)",
                job_id, query, industry, queries, phase
            )
        except Exception as e:
            logger.warning(f"Failed to store job in database: {e}")
            raise

    async def get_job(self, job_id: str):
        """Get a job from the database."""
        try:
            return await self.db.fetch_one("SELECT * FROM jobs WHERE job_id = $1", job_id)
        except Exception as e:
            logger.warning(f"Failed to fetch job from database: {e}")
            return None

    async def get_job_counts(self, job_id: str):
        """Get counts for a job from the database."""
        try:
            product_count = await self.db.fetch_val(
                "SELECT COUNT(*) FROM products WHERE job_id = $1", job_id
            ) or 0
            
            video_count = await self.db.fetch_val(
                "SELECT COUNT(*) FROM videos WHERE job_id = $1", job_id
            ) or 0
            
            match_count = await self.db.fetch_val(
                "SELECT COUNT(*) FROM matches WHERE job_id = $1", job_id
            ) or 0
            
            return product_count, video_count, match_count
        except Exception as e:
            logger.warning(f"Failed to fetch counts from database: {e}")
            return 0, 0, 0

    async def update_job_phase(self, job_id: str, new_phase: str):
        """Update the phase of a job."""
        try:
            await self.db.execute(
                "UPDATE jobs SET phase = $1, updated_at = NOW() WHERE job_id = $2",
                new_phase, job_id
            )
        except Exception as e:
            logger.error(f"Failed to update job phase: {e}")
            raise

    async def get_jobs_for_phase_update(self):
        """Get all jobs that are not completed or failed."""
        try:
            return await self.db.fetch_all(
                "SELECT job_id, phase FROM jobs WHERE phase NOT IN ('completed', 'failed')"
            )
        except Exception as e:
            logger.error(f"Failed to fetch jobs for phase update: {e}")
            return []

    async def get_job_industry(self, job_id: str):
        """Get the industry for a job."""
        try:
            job_record = await self.db.fetch_one(
                "SELECT industry FROM jobs WHERE job_id = $1", job_id
            )
            return job_record["industry"] if job_record else "unknown"
        except Exception as e:
            logger.error(f"Failed to fetch job industry: {e}")
            return "unknown"

    async def get_job_age(self, job_id: str):
        """Get the age of a job in seconds."""
        try:
            return await self.db.fetch_val(
                "SELECT EXTRACT(EPOCH FROM (NOW() - created_at)) FROM jobs WHERE job_id = $1", 
                job_id
            )
        except Exception as e:
            logger.error(f"Failed to fetch job age: {e}")
            return None

    async def get_features_counts(self, job_id: str):
        """Get counts of features for products and videos."""
        try:
            # Count products with features (embeddings or keypoints)
            products_with_features = await self.db.fetch_val(
                "SELECT COUNT(DISTINCT product_id) FROM product_images WHERE product_id IN (SELECT product_id FROM products WHERE job_id = $1) AND (emb_rgb IS NOT NULL OR kp_blob_path IS NOT NULL)", 
                job_id
            ) or 0
            
            # Count videos with features
            videos_with_features = await self.db.fetch_val(
                "SELECT COUNT(DISTINCT video_id) FROM video_frames WHERE video_id IN (SELECT video_id FROM videos WHERE job_id = $1) AND (emb_rgb IS NOT NULL OR kp_blob_path IS NOT NULL)", 
                job_id
            ) or 0
            
            return products_with_features, videos_with_features
        except Exception as e:
            logger.error(f"Failed to fetch features counts: {e}")
            return 0, 0