import os
import re
import asyncio
from typing import List, Dict, Any, Callable, Protocol
from pathlib import Path
from datetime import datetime, timedelta
from common_py.logging_config import configure_logging
from .interface import PlatformCrawlerInterface
from .youtube_searcher import YoutubeSearcher
from .youtube_downloader import YoutubeDownloader
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
        
        # Ensure download directory exists
        Path(download_dir).mkdir(parents=True, exist_ok=True)
        
        all_videos = []
        
        for query in queries:
            try:
                # Skip URL-like inputs
                if is_url_like(query):
                    logger.info(f"Skipping URL-like query: {query}")
                    continue
                
                logger.info(f"Searching YouTube for: {query}")
                
                # Search for videos using yt-dlp
                search_results = await self.searcher.search_youtube(query, recency_days, num_ytb_videos)

                logger.info(f"Found {len(search_results)} videos for query '{query}'")
                
                # Add to our results
                all_videos.extend(search_results)
                
            except Exception as e:
                logger.error(f"Failed to search for query '{query}': {str(e)}")
                continue
        
        logger.info(f"Total videos found across all queries: {len(all_videos)}")
        
        # Deduplicate by video_id
        unique_videos = {}
        for video in all_videos:
            video_id = video['video_id']
            if video_id not in unique_videos:
                unique_videos[video_id] = video
        
        logger.info(f"Unique videos after deduplication: {len(unique_videos)}")
        
        # Download videos
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
        
        logger.info(f"Successfully downloaded {len(downloaded_videos)} videos out of {len(unique_videos)} unique videos")
        return downloaded_videos
    
    