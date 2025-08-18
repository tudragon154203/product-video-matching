import uuid
import os
import logging
from typing import Dict, Any, List
from pathlib import Path
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import VideoCRUD, VideoFrameCRUD
from common_py.models import Video, VideoFrame
from fetcher.video_fetcher import VideoFetcher
from fetcher.keyframe_extractor import KeyframeExtractor
from platform_crawler.interface import PlatformCrawlerInterface
from platform_crawler.mock_crawler import MockPlatformCrawler
from platform_crawler.youtube_crawler import YoutubeCrawler
from handlers.event_emitter import EventEmitter
from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler")


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
        self.event_emitter = EventEmitter(broker)
    
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
                # For YouTube, use VIDEO_DIR/youtube as download directory
                if platform == "youtube":
                    download_dir = os.path.join(config.VIDEO_DIR, "youtube")
                else:
                    # For other platforms, use the existing structure
                    download_dir = str(self.keyframe_extractor.videos_dir / platform)
                
                # Ensure download directory exists
                Path(download_dir).mkdir(parents=True, exist_ok=True)
                
                platform_videos = await self.video_fetcher.search_platform_videos(
                    platform, queries, recency_days, download_dir, num_videos=3
                )
                all_videos.extend(platform_videos)
            
            # Handle zero-asset case (no videos found)
            if not all_videos:
                logger.info("No videos found for job {job_id}", job_id=job_id)
                
                # Publish zero asset event
                await self.event_emitter.publish_zero_asset_event(job_id)
                
                # Publish collections completed event
                await self.event_emitter.publish_videos_collections_completed(job_id)
                
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
            await self.event_emitter.publish_videos_keyframes_ready_batch(job_id, total_frames)
            
            # Process each video
            for video_data in all_videos:
                await self.process_video(video_data, job_id)
            
            # Emit videos collections completed event
            await self.event_emitter.publish_videos_collections_completed(job_id)
            
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
                await self.event_emitter.publish_videos_keyframes_ready(
                    video.video_id, frame_data, job_id
                )
            
            logger.info("Processed video", video_id=video.video_id, 
                       frame_count=len(frame_data))
            
        except Exception as e:
            logger.error(f"Failed to process video: {str(e)}", extra={"video_data": video_data})
    
    def _initialize_platform_crawlers(self, data_root: str) -> Dict[str, PlatformCrawlerInterface]:
        """Initialize platform crawlers for each supported platform"""
        crawlers = {}
        
        # Use real YouTube crawler
        crawlers["youtube"] = YoutubeCrawler()
        
        # Use mock crawlers for other platforms (not implemented yet)
        crawlers["bilibili"] = MockPlatformCrawler("bilibili")
        crawlers["douyin"] = MockPlatformCrawler("douyin")
        crawlers["tiktok"] = MockPlatformCrawler("tiktok")
        
        return crawlers
    