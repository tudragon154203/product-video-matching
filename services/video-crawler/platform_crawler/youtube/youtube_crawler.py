import os
import re
import asyncio
from typing import List, Dict, Any, Callable, Protocol
from pathlib import Path
from datetime import datetime, timedelta
from common_py.logging_config import configure_logging
from platform_crawler.interface import PlatformCrawlerInterface
from platform_crawler.youtube.youtube_searcher import YoutubeSearcher
from platform_crawler.youtube.youtube_downloader import YoutubeDownloader
from utils.youtube_utils import is_url_like, sanitize_filename

logger = configure_logging("video-crawler")


class YoutubeCrawler(PlatformCrawlerInterface):
    """YouTube video crawler using yt-dlp for search and download"""
    
    def __init__(self):
        self.platform_name = "youtube"
        self.searcher = YoutubeSearcher(self.platform_name)
        self.downloader = YoutubeDownloader()
    
    async def search_and_download_videos(
        self, queries: List[str], recency_days: int, download_dir: str, num_ytb_videos: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for videos on YouTube and download them
        
        Args:
            queries: List of search queries (keywords only)
            recency_days: How many days back to search for videos
            download_dir: Directory path where videos should be saved (should be {VIDEO_DIR}/youtube)
            num_ytb_videos: Number of YouTube videos to search for per query
                (actual downloaded videos may be fewer due to filtering)
            
        Returns:
            List of video metadata dictionaries with required fields
        """
        logger.info(f"Starting search_and_download_videos with {len(queries)} queries, recency_days={recency_days}, num_ytb_videos={num_ytb_videos}")
        
        Path(download_dir).mkdir(parents=True, exist_ok=True)
        
        all_videos = await self._search_videos_for_queries(queries, recency_days, num_ytb_videos)
        logger.info(f"Total videos found across all queries: {len(all_videos)}")
        
        unique_videos = self._deduplicate_videos(all_videos)
        logger.info(f"Unique videos after deduplication: {len(unique_videos)}")
        
        downloaded_videos = await self._download_unique_videos(unique_videos, download_dir)
        logger.info(f"Successfully downloaded {len(downloaded_videos)} videos out of {len(unique_videos)} unique videos")
        
        return downloaded_videos
    
    async def _search_videos_for_queries(self, queries: List[str], recency_days: int, num_ytb_videos: int) -> List[Dict[str, Any]]:
        all_videos = []
        for query in queries:
            try:
                if is_url_like(query):
                    logger.info(f"Skipping URL-like query: {query}")
                    continue
                
                logger.info(f"Searching YouTube for: {query}")
                search_results = await self.searcher.search_youtube(query, recency_days, num_ytb_videos)
                logger.info(f"Found {len(search_results)} videos for query '{query}'")
                all_videos.extend(search_results)
            except Exception as e:
                logger.error(f"Failed to search for query '{query}': {str(e)}")
                continue
        return all_videos

    def _deduplicate_videos(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        unique_videos = {}
        for video in videos:
            video_id = video['video_id']
            if video_id not in unique_videos:
                unique_videos[video_id] = video
        return unique_videos

    async def _download_unique_videos(self, unique_videos: Dict[str, Any], download_dir: str) -> List[Dict[str, Any]]:
        downloaded_videos = []
        for video in unique_videos.values():
            try:
                logger.info(f"Attempting to download video: {video['title']} ({video['video_id']})")
                downloaded_video = await self.downloader.download_video(video, download_dir)
                if downloaded_video:
                    downloaded_videos.append(downloaded_video)
                    logger.info(f"Successfully downloaded video: {video['title']} ({video['video_id']})")
                else:
                    logger.warning(f"Failed to download video: {video['title']} ({video['video_id']})")
            except Exception as e:
                logger.error(f"Failed to download video {video['video_id']}: {str(e)}")
                continue
        return downloaded_videos
    
    