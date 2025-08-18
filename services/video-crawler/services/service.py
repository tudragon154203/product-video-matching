import uuid
import logging
from typing import Dict, Any, List
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import VideoCRUD, VideoFrameCRUD
from common_py.models import Video, VideoFrame
from fetcher.video_fetcher import VideoFetcher
from fetcher.keyframe_extractor import KeyframeExtractor
from platform_crawler.interface import PlatformCrawlerInterface
from platform_crawler.mock_crawler import MockPlatformCrawler

logger = logging.getLogger("video-crawler")


class VideoCrawlerService:
    """Main service class for mvideo crawl"""
    
    def __init__(self, db: DatabaseManager, broker: MessageBroker, data_root: str):
        self.db = db
        self.broker = broker
        self.video_crud = VideoCRUD(db)
        self.frame_crud = VideoFrameCRUD(db)
        self.platform_crawlers = self._initialize_platform_crawlers(data_root)
        self.video_fetcher = VideoFetcher(platform_crawlers=self.platform_crawlers)
        self.keyframe_extractor = KeyframeExtractor(data_root)
    
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
            
            # Use VideoFetcher to search videos across platforms
            for platform in platforms:
                platform_dir = self.keyframe_extractor.videos_dir / platform
                platform_dir.mkdir(parents=True, exist_ok=True)
                
                platform_videos = await self.video_fetcher.search_platform_videos(
                    platform, queries, recency_days, str(platform_dir)
                )
                all_videos.extend(platform_videos)
            
            # Handle zero-asset case (no videos found)
            if not all_videos:
                logger.info("No videos found for job {job_id}", job_id=job_id)
                
                # Publish batch event with zero keyframes
                batch_event_id = str(uuid.uuid4())
                await self.broker.publish_event(
                    "videos.keyframes.ready.batch",
                    {
                        "job_id": job_id,
                        "event_id": batch_event_id,
                        "total_keyframes": 0
                    },
                    correlation_id=job_id
                )
                logger.info("Published batch keyframes ready event with zero keyframes",
                           job_id=job_id,
                           total_keyframes=0,
                           batch_event_id=batch_event_id)
                
                # Publish collections completed event
                event_id = str(uuid.uuid4())
                await self.broker.publish_event(
                    "videos.collections.completed",
                    {
                        "job_id": job_id,
                        "event_id": event_id
                    },
                    correlation_id=job_id
                )
                
                logger.info("Completed video search with zero videos",
                           job_id=job_id,
                           total_videos=0)
                return
            
            # Calculate total frames across all candidate videos
            total_frames = 0
            for video_data in all_videos:
                # Extract keyframes to count them without saving to DB
                keyframes = await self.keyframe_extractor.extract_keyframes(video_data["url"], "temp_count")
                total_frames += len(keyframes)
            
            # Emit batch keyframes ready event before processing individual videos
            batch_event_id = str(uuid.uuid4())
            await self.broker.publish_event(
                "videos.keyframes.ready.batch",
                {
                    "job_id": job_id,
                    "event_id": batch_event_id,
                    "total_keyframes": total_frames
                },
                correlation_id=job_id
            )
            logger.info("DUPLICATE DETECTION: Published batch keyframes ready event",
                       job_id=job_id,
                       total_keyframes=total_frames,
                       batch_event_id=batch_event_id)
            
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
            logger.error(f"Failed to process video search request: {str(e)}")
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
            keyframes = await self.keyframe_extractor.extract_keyframes(video_data["url"], video.video_id)
            
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
            logger.error(f"Failed to process video: {str(e)}", extra={"video_data": video_data})
    
    def _initialize_platform_crawlers(self, data_root: str) -> Dict[str, PlatformCrawlerInterface]:
        """Initialize platform crawlers for each supported platform"""
        crawlers = {}
        
        # For now, use mock crawlers for all platforms
        # In production, these would be replaced with real implementations
        crawlers["youtube"] = MockPlatformCrawler("youtube")
        crawlers["bilibili"] = MockPlatformCrawler("bilibili")
        crawlers["douyin"] = MockPlatformCrawler("douyin")
        crawlers["tiktok"] = MockPlatformCrawler("tiktok")
        
        return crawlers
    