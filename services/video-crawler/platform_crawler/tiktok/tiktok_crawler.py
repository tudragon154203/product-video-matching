"""
TikTok Platform Crawler implementing the PlatformCrawlerInterface
"""
import asyncio
from typing import List, Dict, Any
from pathlib import Path
from common_py.logging_config import configure_logging
from platform_crawler.interface import PlatformCrawlerInterface
from .tiktok_searcher import TikTokSearcher
from .tiktok_downloader import TikTokDownloader
from config_loader import config

logger = configure_logging("tiktok-crawler")


class TikTokCrawler(PlatformCrawlerInterface):
    """
    TikTok video crawler using TikTok API for search and download
    Implements PlatformCrawlerInterface for integration with the video crawler system
    """
    
    def __init__(self):
        self.platform_name = "tiktok"
        self.searcher = TikTokSearcher(self.platform_name)
        self.downloader = None
    
    async def search_and_download_videos(
        self, 
        queries: List[str], 
        recency_days: int, 
        download_dir: str, 
        num_videos: int
    ) -> List[Dict[str, Any]]:
        """
        Search for videos on TikTok and download them
        
        Args:
            queries: List of search queries (keywords only)
            recency_days: How many days back to search for videos
            download_dir: Directory path where videos should be saved
            num_videos: Maximum number of videos to return per query
            
        Returns:
            List of video metadata dictionaries with keys:
                - platform: Platform identifier ("tiktok")
                - url: Video URL
                - title: Video title
                - duration_s: Video duration in seconds
                - video_id: Unique identifier for the video
                - local_path: Full path to the downloaded video file
                - author: Video author username
                - view_count: Number of views
                - like_count: Number of likes
                - create_time: Video creation timestamp
        """
        if not queries:
            logger.warning("No search queries provided for TikTok")
            return []
        
        try:
            # Ensure download directory exists
            Path(download_dir).mkdir(parents=True, exist_ok=True)
            
            logger.info("Starting TikTok video search and download", 
                       queries=queries, 
                       recency_days=recency_days,
                       num_videos=num_videos,
                       download_dir=download_dir)
            
            # Step 1: Search for videos
            search_results = await self._search_videos(queries, recency_days, num_videos)
            
            if not search_results:
                logger.info("No videos found for TikTok search", queries=queries)
                return []
            
            logger.info("Found TikTok videos for download", count=len(search_results))
            
            # Step 2: Download videos
            downloaded_videos = await self._download_videos(search_results, download_dir)
            
            # Step 3: Format results for the platform interface
            formatted_results = self._format_results(downloaded_videos)
            
            logger.info("Completed TikTok search and download", 
                       searched=len(search_results),
                       downloaded=len(formatted_results))
            
            return formatted_results
            
        except Exception as e:
            logger.error("Failed to search and download TikTok videos", 
                        queries=queries, error=str(e))
            return []
    
    async def _search_videos(
        self, 
        queries: List[str], 
        recency_days: int, 
        num_videos: int
    ) -> List[Dict[str, Any]]:
        """
        Search for videos using the TikTok searcher
        
        Args:
            queries: List of search keywords
            recency_days: How many days back to search
            num_videos: Maximum number of videos per query
            
        Returns:
            List of video metadata from search results
        """
        try:
            # Check if Vietnam region optimization is enabled
            if config.TIKTOK_VIETNAM_REGION:
                logger.info("Using Vietnam-specific TikTok search")
                search_results = await self.searcher.search_vietnamese_content(
                    queries, recency_days, num_videos
                )
            else:
                logger.info("Using general TikTok keyword search")
                search_results = await self.searcher.search_videos_by_keywords(
                    queries, recency_days, num_videos
                )
            
            return search_results
            
        except Exception as e:
            logger.error("Failed to search TikTok videos", error=str(e))
            return []
    
    async def _download_videos(
        self, 
        videos: List[Dict[str, Any]], 
        download_dir: str
    ) -> List[Dict[str, Any]]:
        """
        Download the searched videos using the TikTok downloader
        
        Args:
            videos: List of video metadata from search
            download_dir: Directory to save videos
            
        Returns:
            List of video metadata with local_path added
        """
        if not videos:
            return []
        
        try:
            # Use the downloader to download videos
            async with TikTokDownloader() as downloader:
                downloaded_videos = await downloader.download_multiple_videos(
                    videos, 
                    download_dir,
                    max_concurrent=config.NUM_PARALLEL_DOWNLOADS
                )
            
            return downloaded_videos
            
        except Exception as e:
            logger.error("Failed to download TikTok videos", error=str(e))
            return []
    
    def _format_results(self, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format video results to match PlatformCrawlerInterface requirements
        
        Args:
            videos: List of video metadata with local paths
            
        Returns:
            List of formatted video metadata dictionaries
        """
        formatted_videos = []
        
        for video in videos:
            try:
                # Check that video was actually downloaded
                if not video.get('local_path'):
                    logger.warning("Skipping video without local_path", 
                                 video_id=video.get('video_id'))
                    continue
                
                formatted_video = {
                    "platform": self.platform_name,
                    "url": video.get('url', ''),
                    "title": video.get('title', f"TikTok video {video.get('video_id', 'unknown')}"),
                    "duration_s": video.get('duration_s', 0),
                    "video_id": video.get('video_id', ''),
                    "local_path": video.get('local_path', ''),
                    
                    # Additional TikTok-specific metadata
                    "author": video.get('author', ''),
                    "author_name": video.get('author_name', ''),
                    "view_count": video.get('view_count', 0),
                    "like_count": video.get('like_count', 0),
                    "share_count": video.get('share_count', 0),
                    "comment_count": video.get('comment_count', 0),
                    "create_time": video.get('create_time', 0),
                }
                
                formatted_videos.append(formatted_video)
                
            except Exception as e:
                logger.warning("Error formatting video result", 
                             video_id=video.get('video_id'), error=str(e))
                continue
        
        return formatted_videos
    
    def get_platform_name(self) -> str:
        """Get the platform name"""
        return self.platform_name
    
    async def health_check(self) -> bool:
        """
        Perform a health check to verify TikTok API connectivity
        
        Returns:
            True if TikTok API is accessible, False otherwise
        """
        try:
            logger.info("Performing TikTok API health check")
            
            # Try to search with a simple query as a health check
            health_videos = await self.searcher.search_videos_by_keywords(
                queries=["test"], recency_days=7, num_videos=1
            )
            
            is_healthy = len(health_videos) >= 0  # Even 0 results means API is working
            
            logger.info("TikTok API health check completed", healthy=is_healthy)
            return is_healthy
            
        except Exception as e:
            logger.error("TikTok API health check failed", error=str(e))
            return False