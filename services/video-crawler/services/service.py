import uuid
import os
from typing import Dict, Any, List
from pathlib import Path
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import VideoCRUD, VideoFrameCRUD
from common_py.models import Video, VideoFrame
from fetcher.video_fetcher import VideoFetcher
from keyframe_extractor.length_adaptive_extractor import LengthAdaptiveKeyframeExtractor
from platform_crawler.interface import PlatformCrawlerInterface
from platform_crawler.mock_crawler import MockPlatformCrawler
from platform_crawler.youtube.youtube_crawler import YoutubeCrawler
from handlers.event_emitter import EventEmitter
from common_py.logging_config import configure_logging
from config_loader import config
from vision_common import JobProgressManager

logger = configure_logging("video-crawler")


class VideoCrawlerService:
    """Main service class for mvideo crawl"""
    
    def __init__(self, db: DatabaseManager, broker: MessageBroker):
        self.db = db
        self.broker = broker
        self.video_crud = VideoCRUD(db)
        self.frame_crud = VideoFrameCRUD(db)
        self.platform_crawlers = self._initialize_platform_crawlers()
        self.video_fetcher = VideoFetcher(platform_crawlers=self.platform_crawlers)
        self.keyframe_extractor = LengthAdaptiveKeyframeExtractor()
        self.event_emitter = EventEmitter(broker)
        self.job_progress_manager = JobProgressManager(broker)
    
    async def handle_videos_search_request(self, event_data: Dict[str, Any]):
        """Handle video search request with cross-platform parallelism"""
        try:
            job_id = event_data["job_id"]
            industry = event_data["industry"]
            queries = event_data["queries"]
            platforms = event_data["platforms"]
            recency_days = event_data["recency_days"]
            
            logger.info("Processing video search request",
                       job_id=job_id, industry=industry, platforms=platforms)
            
            platform_queries = self._extract_platform_queries(queries, platforms)
            
            # Prepare download directories for each platform
            platform_download_dirs = {}
            for platform in platforms:
                if platform == "youtube":
                    platform_download_dirs[platform] = os.path.join(config.VIDEO_DIR, "youtube")
                else:
                    platform_download_dirs[platform] = os.path.join(config.VIDEO_DIR, platform)
                
                Path(platform_download_dirs[platform]).mkdir(parents=True, exist_ok=True)
            
            # Delegate cross-platform parallelism to VideoFetcher
            all_videos = await self.video_fetcher.search_all_platforms_videos_parallel(
                platforms=platforms,
                queries=platform_queries,
                recency_days=recency_days,
                download_dirs=platform_download_dirs,
                num_videos=config.NUM_VIDEOS,
                job_id=job_id,
                max_concurrent_platforms=config.MAX_CONCURRENT_PLATFORMS
            )
            
            if not all_videos:
                await self._handle_zero_videos_case(job_id)
                return
            
            # Register total videos with JobProgressManager
            await self.job_progress_manager.update_job_progress(job_id, "video", len(all_videos), 0, "crawling")
            
            await self._process_and_emit_videos(all_videos, job_id)
            
            logger.info("Completed video search",
                       job_id=job_id,
                       total_videos=len(all_videos))
            
        except Exception as e:
            logger.error(f"Failed to process video search request: {str(e)}")
            raise

    def _extract_platform_queries(self, queries: Dict[str, Any], platforms: List[str]) -> List[str]:
        platform_queries = []
        if isinstance(queries, dict):
            if "youtube" in platforms and "vi" in queries:
                platform_queries = queries["vi"]
            elif "bilibili" in platforms and "zh" in queries:
                platform_queries = queries["zh"]
            elif "douyin" in platforms and "vi" in queries:
                platform_queries = queries["vi"]
            else:
                for query_list in queries.values():
                    if isinstance(query_list, list):
                        platform_queries.extend(query_list)
        else:
            platform_queries = queries if isinstance(queries, list) else []
        return platform_queries

    async def _handle_zero_videos_case(self, job_id: str):
        logger.info("No videos found for job {job_id}", job_id=job_id)
        await self.event_emitter.publish_videos_collections_completed(job_id)
        logger.info("Completed video search with zero videos",
                   job_id=job_id,
                   total_videos=0)

    async def _process_and_emit_videos(self, all_videos: List[Dict[str, Any]], job_id: str):
        for video_data in all_videos:
            await self.process_video(video_data, job_id)
        await self.event_emitter.publish_videos_collections_completed(job_id)
    
    async def process_video(self, video_data: Dict[str, Any], job_id: str) -> List[Dict[str, Any]]:
        """Process a single video and extract keyframes"""
        try:
            video = await self._create_and_save_video_record(video_data, job_id)
            keyframes_data = await self._extract_and_save_keyframes(video, video_data)
            await self._emit_keyframes_ready_event(video, keyframes_data, job_id)
            
            # Increment processed count for the video
            await self.job_progress_manager.update_job_progress(job_id, "video", 0, 1, "crawling")
            
            logger.info("Processed video", video_id=video.video_id, 
                       frame_count=len(keyframes_data))
            return keyframes_data
            
        except Exception as e:
            logger.error(f"Failed to process video: {str(e)}", extra={"video_data": video_data})
            return [] # Return empty list on error to avoid breaking the sum

    async def _create_and_save_video_record(self, video_data: Dict[str, Any], job_id: str) -> Video:
        video = Video(
            video_id=str(uuid.uuid4()),
            platform=video_data["platform"],
            url=video_data["url"],
            title=video_data["title"],
            duration_s=video_data.get("duration_s")
        )
        await self.db.execute(
            "INSERT INTO videos (video_id, platform, url, title, duration_s, job_id) VALUES ($1, $2, $3, $4, $5, $6)",
            video.video_id, video.platform, video.url,
            video.title, video.duration_s, job_id
        )
        return video

    async def _extract_and_save_keyframes(self, video: Video, video_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Get the local path from video_data if available
        local_path = video_data.get("local_path")
        
        # Extract keyframes from downloaded video or create dummy frames
        keyframes = await self.keyframe_extractor.extract_keyframes(
            video_data["url"], video.video_id, local_path
        )
        
        frame_data = []
        for i, (timestamp, frame_path) in enumerate(keyframes):
            frame_id = f"{video.video_id}_frame_{i}"
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
        return frame_data

    async def _emit_keyframes_ready_event(self, video: Video, keyframes_data: List[Dict[str, Any]], job_id: str):
        if keyframes_data:
            await self.event_emitter.publish_videos_keyframes_ready(
                video.video_id, keyframes_data, job_id
            )
    
    def _initialize_platform_crawlers(self) -> Dict[str, PlatformCrawlerInterface]:
        """Initialize platform crawlers for each supported platform"""
        crawlers = {}

        # Use real YouTube crawler
        crawlers["youtube"] = YoutubeCrawler()


        # Use mock crawlers for other platforms (not implemented yet)
        crawlers["bilibili"] = MockPlatformCrawler("bilibili")
        crawlers["douyin"] = MockPlatformCrawler("douyin")

        return crawlers
    