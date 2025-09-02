from typing import Dict, Any, Optional
from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging

logger = configure_logging("evidence-builder:match_record_manager")

class MatchRecordManager:
    def __init__(self, db: DatabaseManager):
        self.db = db

    async def update_match_record_and_log(self, job_id: str, product_id: str, video_id: str, evidence_path: str):
        await self.db.execute(
            "UPDATE matches SET evidence_path = $1 WHERE product_id = $2 AND video_id = $3 AND job_id = $4",
            evidence_path, product_id, video_id, job_id
        )
        logger.info("Generated evidence", 
                   job_id=job_id,
                   product_id=product_id,
                   video_id=video_id,
                   evidence_path=evidence_path)

    async def get_image_info(self, img_id: str):
        """Get product image information"""
        query = "SELECT local_path, kp_blob_path FROM product_images WHERE img_id = $1"
        return await self.db.fetch_one(query, img_id)
    
    async def get_frame_info(self, frame_id: str):
        """Get video frame information"""
        query = "SELECT local_path, kp_blob_path FROM video_frames WHERE frame_id = $1"
        return await self.db.fetch_one(query, frame_id)
