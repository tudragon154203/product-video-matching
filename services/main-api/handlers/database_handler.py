from common_py.database import DatabaseManager
from typing import Optional, Dict, Any
from common_py.logging_config import configure_logging

logger = configure_logging("main-api")

class DatabaseHandler:
    def __init__(self, db: DatabaseManager):
        self.db = db

    async def store_job(self, job_id: str, query: str, industry: str, queries: Dict[str, Any], phase: str = "collection"):
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

    async def get_job_phase(self, job_id: str) -> str:
        """Get the current phase of a job."""
        try:
            result = await self.db.fetch_one(
                "SELECT phase FROM jobs WHERE job_id = $1", job_id
            )
            return result["phase"] if result else "unknown"
        except Exception as e:
            logger.error(f"Failed to fetch job phase: {e}")
            return "unknown"

    async def store_phase_event(self, event_id: str, job_id: str, event_name: str):
        """Store a phase event in the database."""
        try:
            await self.db.execute(
                "INSERT INTO phase_events (event_id, job_id, name) VALUES ($1, $2, $3)",
                event_id, job_id, event_name
            )
        except Exception as e:
            logger.error(f"Failed to store phase event: {e}")
            raise

    async def has_phase_event(self, job_id: str, event_name: str) -> bool:
        """Check if a phase event has been received for a job."""
        try:
            result = await self.db.fetch_val(
                "SELECT COUNT(*) FROM phase_events WHERE job_id = $1 AND name = $2",
                job_id, event_name
            )
            count = result or 0
            logger.info(f"Checking phase event (job_id: {job_id}, event_name: {event_name}, count: {count})")
            if count > 1:
                logger.warning(f"MULTIPLE phase events found for same job/event (job_id: {job_id}, event_name: {event_name}, count: {count})")
            return count > 0
        except Exception as e:
            logger.error(f"Failed to check phase event: {e}")
            return False

    async def get_job_asset_types(self, job_id: str) -> Dict[str, bool]:
        """Get the asset types (images, videos) for a job.
        
        Returns a dictionary indicating which asset types are present:
        - {"images": True, "videos": True} for mixed jobs
        - {"images": True, "videos": False} for product-only jobs
        - {"images": False, "videos": True} for video-only jobs
        - {"images": False, "videos": False} for zero-asset jobs
        """
        try:
            # Get counts of products and videos for this job
            product_count, video_count, _ = await self.get_job_counts(job_id)
            
            # Get counts of products and videos with features
            products_with_features, videos_with_features = await self.get_features_counts(job_id)
            
            # Determine asset types based on presence of products/videos
            # According to sprint 7 requirements, we need to handle zero-asset cases
            has_images = product_count > 0 or products_with_features > 0
            has_videos = video_count > 0 or videos_with_features > 0
            
            logger.info(f"Job {job_id} asset types determined: images={has_images} (products={product_count}, with_features={products_with_features}), videos={has_videos} (videos={video_count}, with_features={videos_with_features})")
            
            return {"images": has_images, "videos": has_videos}
        except Exception as e:
            logger.error(f"Failed to determine job asset types for job {job_id}: {str(e)}")
            # Fallback to both being True to maintain current behavior
            return {"images": True, "videos": True}
    
    async def clear_phase_events(self, job_id: str):
        """Clear all phase events for a job (for testing/reset purposes)."""
        try:
            await self.db.execute(
                "DELETE FROM phase_events WHERE job_id = $1",
                job_id
            )
        except Exception as e:
            logger.error(f"Failed to clear phase events: {e}")
            raise