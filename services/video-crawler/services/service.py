import uuid
import structlog
from typing import Dict, Any, List
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import VideoCRUD, VideoFrameCRUD
from common_py.models import Video, VideoFrame
from fetcher.video_api_fetcher import VideoAPIFetcher

logger = structlog.get_logger()


class VideoCrawlerService:
    """Main service class for mvideo crawl"""
    
    def __init__(self, db: DatabaseManager, broker: MessageBroker, data_root: str):
        self.db = db
        self.broker = broker
        self.video_crud = VideoCRUD(db)
        self.frame_crud = VideoFrameCRUD(db)
        self.fetcher = VideoAPIFetcher(data_root)
    
    async def handle_videos_search_request(self, event_data: Dict[str, Any]):
        """Handle video search request"""
        try:
            job_id = event_data["job_id"]
            industry = event_data["industry"]
            queries = event_data["queries"]
            platforms = event_data["platforms"]
            recency_days = event_data["recency_days"]
            
            logger.info("Processing video search request",
                       job_id=job_id, industry=industry, platforms=platforms)
            
            # Search videos on each platform
            all_videos = []
            
            for platform in platforms:
                platform_queries = []
                if platform == "youtube" and "vi" in queries:
                    platform_queries = queries["vi"]
                elif platform == "bilibili" and "zh" in queries:
                    platform_queries = queries["zh"]
                    
                if platform_queries:
                    if platform == "youtube":
                        videos = await self.fetcher.search_youtube_videos(platform_queries, recency_days)
                        all_videos.extend(videos)
                    elif platform == "bilibili":
                        videos = await self.fetcher.search_bilibili_videos(platform_queries, recency_days)
                        all_videos.extend(videos)
            
            # Process each video
            for video_data in all_videos:
                await self.process_video(video_data, job_id)
            
            # Emit videos collections completed event
            event_id = str(uuid.uuid4())
            await self.broker.publish_event(
                "videos.collections.completed",
                {
                    "job_id": job_id,
                    "event_id": event_id
                },
                correlation_id=job_id
            )
            
            logger.info("Completed video search", 
                       job_id=job_id, 
                       total_videos=len(all_videos))
            
        except Exception as e:
            logger.error("Failed to process video search request", error=str(e))
            raise
    
    async def process_video(self, video_data: Dict[str, Any], job_id: str):
        """Process a single video and extract keyframes"""
        try:
            # Create video record
            video = Video(
                video_id=str(uuid.uuid4()),
                platform=video_data["platform"],
                url=video_data["url"],
                title=video_data["title"],
                duration_s=video_data.get("duration_s"),
                published_at=video_data.get("published_at")
            )
            
            # Save to database
            await self.db.execute(
                "INSERT INTO videos (video_id, platform, url, title, duration_s, published_at, job_id) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                video.video_id, video.platform, video.url, 
                video.title, video.duration_s, video.published_at, job_id
            )
            
            # Download video and extract keyframes
            keyframes = await self.fetcher.extract_keyframes(video_data["url"], video.video_id)
            
            # Process each keyframe
            frame_data = []
            for i, (timestamp, frame_path) in enumerate(keyframes):
                frame_id = f"{video.video_id}_frame_{i}"
                
                # Create frame record
                frame = VideoFrame(
                    frame_id=frame_id,
                    video_id=video.video_id,
                    ts=timestamp,
                    local_path=frame_path
                )
                
                await self.frame_crud.create_video_frame(frame)
                
                frame_data.append({
                    "frame_id": frame_id,
                    "ts": timestamp,
                    "local_path": frame_path
                })
            
            # Emit keyframes ready event
            if frame_data:
                await self.broker.publish_event(
                    "videos.keyframes.ready",
                    {
                        "video_id": video.video_id,
                        "frames": frame_data,
                        "job_id": job_id  # Add job_id for tracking
                    },
                    correlation_id=job_id
                )
            
            logger.info("Processed video", video_id=video.video_id, 
                       frame_count=len(frame_data))
            
        except Exception as e:
            logger.error("Failed to process video", video_data=video_data, error=str(e))