from typing import Optional, List, Dict, Any
from ..database import DatabaseManager
from ..models import Video

class VideoCRUD:
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def create_video(self, video: Video) -> str:
        """Create a new video"""
        query = """
        INSERT INTO videos (video_id, platform, url, title, duration_s, published_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING video_id
        """
        return await self.db.fetch_val(
            query, video.video_id, video.platform, video.url,
            video.title, video.duration_s, video.published_at
        )
    
    async def get_video(self, video_id: str) -> Optional[Video]:
        """Get a video by ID"""
        query = "SELECT * FROM videos WHERE video_id = $1"
        row = await self.db.fetch_one(query, video_id)
        return Video(**row) if row else None
    
    async def list_videos(self, limit: int = 100, offset: int = 0) -> List[Video]:
        """List videos with pagination"""
        query = "SELECT * FROM videos ORDER BY created_at DESC LIMIT $1 OFFSET $2"
        rows = await self.db.fetch_all(query, limit, offset)
        return [Video(**row) for row in rows]
