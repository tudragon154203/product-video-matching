from typing import Optional, List, Dict, Any
from ..database import DatabaseManager
from ..models import VideoFrame

class VideoFrameCRUD:
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def create_video_frame(self, frame: VideoFrame) -> str:
        """Create a new video frame"""
        query = """
        INSERT INTO video_frames (frame_id, video_id, ts, local_path, kp_blob_path)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING frame_id
        """
        return await self.db.fetch_val(
            query, frame.frame_id, frame.video_id, frame.ts,
            frame.local_path, frame.kp_blob_path
        )
    
    async def update_embeddings(self, frame_id: str, emb_rgb: List[float], emb_gray: List[float]):
        """Update embeddings for a video frame"""
        # Convert lists to vector format for PostgreSQL
        rgb_vector = '[' + ','.join(map(str, emb_rgb)) + ']'
        gray_vector = '[' + ','.join(map(str, emb_gray)) + ']'
        
        query = """
        UPDATE video_frames 
        SET emb_rgb = $2::vector, emb_gray = $3::vector
        WHERE frame_id = $1
        """
        await self.db.execute(query, frame_id, rgb_vector, gray_vector)
    
    async def get_video_frame(self, frame_id: str) -> Optional[VideoFrame]:
        """Get a video frame by ID"""
        query = "SELECT * FROM video_frames WHERE frame_id = $1"
        row = await self.db.fetch_one(query, frame_id)
        return VideoFrame(**row) if row else None
    
    async def list_video_frames(self, video_id: str) -> List[VideoFrame]:
        """List frames for a video"""
        query = "SELECT * FROM video_frames WHERE video_id = $1 ORDER BY ts"
        rows = await self.db.fetch_all(query, video_id)
        return [VideoFrame(**row) for row in rows]
    
    async def list_video_frames_by_video(self, video_id: str, limit: int = 100, offset: int = 0,
                                       sort_by: str = "ts", order: str = "ASC") -> List[VideoFrame]:
        """List frames for a video with pagination and sorting"""
        # Validate sort_by field
        valid_sort_fields = ["ts", "frame_id"]
        if sort_by not in valid_sort_fields:
            sort_by = "ts"
        
        # Validate order
        order = order.upper() if order.upper() in ["ASC", "DESC"] else "ASC"
        
        query = f"""
        SELECT * FROM video_frames
        WHERE video_id = $1
        ORDER BY {sort_by} {order}
        LIMIT $2 OFFSET $3
        """
        
        rows = await self.db.fetch_all(query, video_id, limit, offset)
        return [VideoFrame(**row) for row in rows]
    
    async def count_video_frames_by_video(self, video_id: str) -> int:
        """Count frames for a video"""
        query = "SELECT COUNT(*) FROM video_frames WHERE video_id = $1"
        return await self.db.fetch_val(query, video_id)
    
    async def count_video_frames_by_job(self, job_id: str, video_id: Optional[str] = None, has_feature: Optional[str] = None) -> int:
        """Count frames for a job with optional video_id and feature filtering."""
        query = """
            SELECT COUNT(*)
            FROM video_frames vf
            JOIN videos v ON vf.video_id = v.video_id
            WHERE v.job_id = $1
        """
        params = [job_id]
        param_index = 2
        
        # Add video_id filter if provided
        if video_id:
            query += f" AND vf.video_id = ${param_index}"
            params.append(video_id)
            param_index += 1
        
        # Add feature filter if provided
        if has_feature:
            if has_feature == "segment":
                query += f" AND vf.masked_local_path IS NOT NULL"
            elif has_feature == "embedding":
                query += f" AND (vf.emb_rgb IS NOT NULL OR vf.emb_gray IS NOT NULL)"
            elif has_feature == "keypoints":
                query += f" AND vf.kp_blob_path IS NOT NULL"
            elif has_feature == "none":
                query += f" AND vf.masked_local_path IS NULL AND vf.emb_rgb IS NULL AND vf.emb_gray IS NULL AND vf.kp_blob_path IS NULL"
            elif has_feature == "any":
                query += f" AND (vf.masked_local_path IS NOT NULL OR vf.emb_rgb IS NOT NULL OR vf.emb_gray IS NOT NULL OR vf.kp_blob_path IS NOT NULL)"
        
        count = await self.db.fetch_val(query, *params)
        return count or 0
    
    async def list_video_frames_by_job_with_features(
        self,
        job_id: str,
        video_id: Optional[str] = None,
        has_feature: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "ts",
        order: str = "ASC"
    ) -> List[VideoFrame]:
        """List frames for a job with optional video_id, feature filtering, pagination and sorting."""
        # Validate sort_by field
        valid_sort_fields = ["ts", "frame_id", "updated_at"]
        if sort_by not in valid_sort_fields:
            sort_by = "ts"
        
        # Validate order
        order = order.upper() if order.upper() in ["ASC", "DESC"] else "ASC"
        
        query = """
            SELECT vf.*
            FROM video_frames vf
            JOIN videos v ON vf.video_id = v.video_id
            WHERE v.job_id = $1
        """
        params = [job_id]
        param_index = 2
        
        # Add video_id filter if provided
        if video_id:
            query += f" AND vf.video_id = ${param_index}"
            params.append(video_id)
            param_index += 1
        
        # Add feature filter if provided
        if has_feature:
            if has_feature == "segment":
                query += f" AND vf.masked_local_path IS NOT NULL"
            elif has_feature == "embedding":
                query += f" AND (vf.emb_rgb IS NOT NULL OR vf.emb_gray IS NOT NULL)"
            elif has_feature == "keypoints":
                query += f" AND vf.kp_blob_path IS NOT NULL"
            elif has_feature == "none":
                query += f" AND vf.masked_local_path IS NULL AND vf.emb_rgb IS NULL AND vf.emb_gray IS NULL AND vf.kp_blob_path IS NULL"
            elif has_feature == "any":
                query += f" AND (vf.masked_local_path IS NOT NULL OR vf.emb_rgb IS NOT NULL OR vf.emb_gray IS NOT NULL OR vf.kp_blob_path IS NOT NULL)"
        
        # Add sorting and pagination
        query += f" ORDER BY vf.{sort_by} {order} LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.extend([limit, offset])
        
        rows = await self.db.fetch_all(query, *params)
        return [VideoFrame(**row) for row in rows]
    
    async def get_video_frames_count(self, video_id: str) -> int:
        """Get the total count of frames for a video"""
        query = "SELECT COUNT(*) FROM video_frames WHERE video_id = $1"
        return await self.db.fetch_val(query, video_id)
