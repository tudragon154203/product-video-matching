import os
import re
import asyncio
import random
from typing import List, Dict, Any, Callable, Protocol
from pathlib import Path
from datetime import datetime, timedelta
from common_py.logging_config import configure_logging
from platform_crawler.interface import PlatformCrawlerInterface
from platform_crawler.youtube.youtube_searcher import YoutubeSearcher
from platform_crawler.youtube.downloader import YoutubeDownloader
from platform_crawler.youtube.youtube_utils import is_url_like, sanitize_filename
from config_loader import config

logger = configure_logging("video-crawler:youtube_crawler")


class YoutubeCrawler(PlatformCrawlerInterface):
    """YouTube video crawler using yt-dlp for search and download"""
    
    def __init__(self):
        self.platform_name = "youtube"
        self.searcher = YoutubeSearcher(self.platform_name)
        self.downloader = YoutubeDownloader()
    
    async def search_and_download_videos(
        self, queries: List[str], recency_days: int, download_dir: str, num_videos: int
    ) -> List[Dict[str, Any]]:
        """
        Search for videos on YouTube and download them
        
        Args:
            queries: List of search queries (keywords only)
            recency_days: How many days back to search for videos
            download_dir: Directory path where videos should be saved (should be {VIDEO_DIR}/youtube)
            num_videos: Number of YouTube videos to search for per query
                (actual downloaded videos may be fewer due to filtering)
            
        Returns:
            List of video metadata dictionaries with required fields
        """
        logger.info(f"Starting search_and_download_videos with {len(queries)} queries, recency_days={recency_days}, num_videos={num_videos}")
        
        Path(download_dir).mkdir(parents=True, exist_ok=True)
        
        all_videos = await self._search_videos_for_queries(queries, recency_days, num_videos)
        logger.info(f"Total videos found across all queries: {len(all_videos)}")
        
        unique_videos = self._deduplicate_videos(all_videos)
        logger.info(f"Unique videos after deduplication: {len(unique_videos)}")
        
        downloaded_videos = await self._download_unique_videos(unique_videos, download_dir)
        logger.info(f"Successfully downloaded {len(downloaded_videos)} videos out of {len(unique_videos)} unique videos")
        
        return downloaded_videos
    
    async def _search_videos_for_queries(self, queries: List[str], recency_days: int, num_ytb_videos: int) -> List[Dict[str, Any]]:
        all_videos = []
        for i, query in enumerate(queries):
            try:
                if is_url_like(query):
                    logger.info(f"Skipping URL-like query: {query}")
                    continue
                
                logger.info(f"Searching YouTube for: {query}")
                search_results = await self.searcher.search_youtube(query, recency_days, num_ytb_videos)
                logger.info(f"Found {len(search_results)} videos for query '{query}'")
                all_videos.extend(search_results)
                
                # Add a small delay between queries to avoid rate limiting
                if i < len(queries) - 1:  # Don't delay after the last query
                    delay = random.uniform(1.0, 3.0)  # Random delay between 1-3 seconds
                    logger.info(f"Waiting {delay:.1f}s before next query to avoid rate limiting")
                    await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Failed to search for query '{query}': {str(e)}")
                # Log the full traceback for debugging
                logger.error(f"Full traceback for query '{query}':", exc_info=True)
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
        videos_list = list(unique_videos.values())
        downloaded_videos = []
        
        # Process videos in parallel with semaphore to limit concurrent downloads
        semaphore = asyncio.Semaphore(config.NUM_PARALLEL_DOWNLOADS)
        
        # Track concurrency for debugging
        active_downloads = 0
        max_concurrent = 0
        
        async def download_single_video(video):
            nonlocal active_downloads, max_concurrent
            
            # Track when semaphore is acquired
            active_downloads += 1
            max_concurrent = max(max_concurrent, active_downloads)
            logger.info(f"[CONCURRENCY] Active downloads: {active_downloads} | Max so far: {max_concurrent} | Starting: {video['title']}")
            
            async with semaphore:  # Acquire semaphore before downloading
                try:
                    downloaded_video = await self.downloader.download_video(video, download_dir)
                    if downloaded_video:
                        logger.info(f"[CONCURRENCY] Active downloads: {active_downloads} | Completed: {video['title']}")
                        return downloaded_video
                    else:
                        logger.warning(f"[CONCURRENCY] Active downloads: {active_downloads} | Failed: {video['title']}")
                        return None
                except Exception as e:
                    logger.error(f"[CONCURRENCY] Active downloads: {active_downloads} | Exception: {video['title']} | Error: {str(e)}")
                    # Log full traceback for debugging
                    logger.error(f"Full traceback for video '{video['title']}':", exc_info=True)
                    return None
                finally:
                    active_downloads -= 1
                    logger.info(f"[CONCURRENCY] Active downloads: {active_downloads} | Finished: {video['title']}")
        
        # Run all downloads in parallel
        logger.info(f"[PARALLEL-START] Starting {len(videos_list)} video downloads with {config.NUM_PARALLEL_DOWNLOADS} concurrent limit")
        start_time = asyncio.get_event_loop().time()
        
        tasks = [download_single_video(video) for video in videos_list]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Filter out failed downloads
        downloaded_videos = [result for result in results if result is not None]
        
        total_time = asyncio.get_event_loop().time() - start_time
        avg_time = total_time / len(videos_list) if len(videos_list) > 0 else 0
        logger.info(f"[PARALLEL-FINISH] Completed {len(downloaded_videos)}/{len(videos_list)} downloads | "
                   f"Max concurrent: {max_concurrent} | Total time: {total_time:.2f}s | "
                   f"Average per download: {avg_time:.2f}s")
        
        return downloaded_videos
    
