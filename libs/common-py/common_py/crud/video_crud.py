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

    async def upsert_video(self, video: Video) -> str:
        """Idempotently insert or update a video, returning video_id.

        Uses ON CONFLICT (video_id) DO UPDATE to ensure idempotency.
        """
        query = """
        INSERT INTO videos (video_id, platform, url, title, duration_s, published_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (video_id) DO UPDATE SET
            platform = EXCLUDED.platform,
            url = EXCLUDED.url,
            title = COALESCE(EXCLUDED.title, videos.title),
            duration_s = COALESCE(EXCLUDED.duration_s, videos.duration_s),
            published_at = COALESCE(EXCLUDED.published_at, videos.published_at)
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
    
    async def list_videos_by_job(self, job_id: str, limit: int = 100, offset: int = 0,
                                search_query: Optional[str] = None, platform: Optional[str] = None,
                                min_frames: Optional[int] = None, sort_by: str = "created_at",
                                order: str = "DESC") -> List[Video]:
        """List videos by job ID with filtering and pagination"""
        conditions = ["job_id = $1"]
        params = [job_id]
        param_count = 1
        
        if search_query:
            param_count += 1
            conditions.append(f"title ILIKE ${param_count}")
            params.append(f"%{search_query}%")
        
        if platform:
            param_count += 1
            conditions.append(f"platform = ${param_count}")
            params.append(platform)
        
        if min_frames is not None:
            param_count += 1
            # Reference the outer query alias 'v' to avoid FROM-clause issues
            conditions.append(
                f"EXISTS (SELECT 1 FROM video_frames vf "
                f"WHERE vf.video_id = v.video_id "
                f"AND vf.created_at >= NOW() - INTERVAL '1 day' "
                f"GROUP BY vf.video_id HAVING COUNT(*) >= ${param_count})"
            )
            params.append(min_frames)
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        # Validate sort_by field (frames_count removed)
        valid_sort_fields = ["created_at", "duration_s", "title", "platform"]
        if sort_by not in valid_sort_fields:
            sort_by = "created_at"
        
        # Validate order
        order = order.upper() if order.upper() in ["ASC", "DESC"] else "DESC"
        
        param_count += 1
        params.append(limit)
        param_count += 1
        params.append(offset)
        
        # Custom platform sorting with priority: youtube, tiktok, douyin, others
        if sort_by == "platform":
            case_statement = """
            CASE
                WHEN lower(platform) = 'youtube' THEN 0
                WHEN lower(platform) = 'tiktok' THEN 1
                WHEN lower(platform) = 'douyin' THEN 2
                ELSE 3
            END
            """
            # When sorting by platform, also sort by recency within each platform group
            # so that newly added videos surface to the top during polling.
            # Keep secondary sort by created_at DESC regardless of platform group order.
            query = f"""
            SELECT v.* FROM videos v
            {where_clause}
            ORDER BY {case_statement} {order}, v.created_at DESC
            LIMIT ${param_count-1} OFFSET ${param_count}
            """
        else:
            query = f"""
            SELECT v.* FROM videos v
            {where_clause}
            ORDER BY v.{sort_by} {order}
            LIMIT ${param_count-1} OFFSET ${param_count}
            """
        
        rows = await self.db.fetch_all(query, *params)
        return [Video(**row) for row in rows]
    
    async def count_videos_by_job(self, job_id: str, search_query: Optional[str] = None,
                                 platform: Optional[str] = None, min_frames: Optional[int] = None) -> int:
        """Count videos by job ID with filtering"""
        conditions = ["job_id = $1"]
        params = [job_id]
        param_count = 1
        
        if search_query:
            param_count += 1
            conditions.append(f"title ILIKE ${param_count}")
            params.append(f"%{search_query}%")
        
        if platform:
            param_count += 1
            conditions.append(f"platform = ${param_count}")
            params.append(platform)
        
        if min_frames is not None:
            param_count += 1
            conditions.append(f"EXISTS (SELECT 1 FROM video_frames vf WHERE vf.video_id = videos.video_id AND vf.created_at >= NOW() - INTERVAL '1 day' GROUP BY vf.video_id HAVING COUNT(*) >= ${param_count})")
            params.append(min_frames)
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        SELECT COUNT(*) FROM videos
        {where_clause}
        """
        
        return await self.db.fetch_val(query, *params)
