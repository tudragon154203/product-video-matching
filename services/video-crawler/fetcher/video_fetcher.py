import asyncio
import time
from typing import List, Dict, Any, Optional
from platform_crawler.interface import PlatformCrawlerInterface
from common_py.logging_config import configure_logging
from config_loader import config

logger = configure_logging("video-crawler:video_fetcher")


class VideoFetcher:
    """Handles video search across multiple platforms using platform crawlers"""
    
    def __init__(self, platform_crawlers: Optional[Dict[str, PlatformCrawlerInterface]] = None):
        self.platform_crawlers = platform_crawlers or {}
    
    async def search_all_platforms_videos_parallel(
        self, 
        platforms: List[str],
        queries: List[str], 
        recency_days: int, 
        download_dirs: Dict[str, str], 
        num_videos: int,
        job_id: str,
        max_concurrent_platforms: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Search videos across multiple platforms in parallel (new cross-platform parallelism implementation)
        
        Args:
            platforms: List of platform names to search
            queries: List of search queries
            recency_days: How many days back to search for videos
            download_dirs: Dictionary mapping platform names to download directories
            num_videos: Number of videos to search for per query per platform
            job_id: Job identifier for logging
            max_concurrent_platforms: Maximum number of concurrent platforms (-1 means no limit)
            
        Returns:
            List of all video metadata dictionaries from all platforms
        """
        if max_concurrent_platforms == -1:  # No limit
            max_concurrent_platforms = len(platforms)
        
        platform_semaphore = asyncio.Semaphore(max_concurrent_platforms)
        
        logger.info("Starting cross-platform video search",
                   job_id=job_id,
                   platforms=platforms,
                   max_concurrent_platforms=max_concurrent_platforms)
        
        async def run_platform(platform: str):
            async with platform_semaphore:
                start_time = time.perf_counter()
                logger.info("platform.start", extra={
                    "job_id": job_id,
                    "platform": platform,
                    "query_count": len(queries),
                    "started_at": start_time
                })
                
                try:
                    if platform not in self.platform_crawlers:
                        logger.warning(f"Platform crawler not available for: {platform}")
                        return []
                    
                    download_dir = download_dirs.get(platform, "")
                    if not download_dir:
                        logger.warning(f"No download directory specified for platform: {platform}")
                        return []
                    
                    crawler = self.platform_crawlers[platform]
                    videos = await crawler.search_and_download_videos(
                        queries=queries,
                        recency_days=recency_days,
                        download_dir=download_dir,
                        num_videos=num_videos
                    )
                    
                    end_time = time.perf_counter()
                    elapsed_ms = int((end_time - start_time) * 1000)
                    
                    logger.info("platform.done", extra={
                        "job_id": job_id,
                        "platform": platform,
                        "video_count": len(videos),
                        "elapsed_ms": elapsed_ms,
                        "started_at": start_time,
                        "ended_at": end_time
                    })
                    
                    logger.info(f"Found {len(videos)} videos on {platform}",
                               platform=platform, video_count=len(videos))
                    return videos
                    
                except Exception as e:
                    end_time = time.perf_counter()
                    elapsed_ms = int((end_time - start_time) * 1000)
                    
                    logger.error("platform.error", extra={
                        "job_id": job_id,
                        "platform": platform,
                        "error": repr(e),
                        "elapsed_ms": elapsed_ms,
                        "started_at": start_time,
                        "ended_at": end_time
                    })
                    logger.error(f"Failed to search videos on {platform}",
                                platform=platform, error=str(e))
                    return []
        
        # Run all platforms in parallel with exception handling
        results = await asyncio.gather(
            *[run_platform(platform) for platform in platforms],
            return_exceptions=True
        )
        
        # Process results, handling exceptions
        all_videos = []
        platforms_attempted = len(platforms)
        platforms_success = 0
        platforms_failed = 0
        
        for i, result in enumerate(results):
            platform = platforms[i]
            if isinstance(result, Exception):
                logger.error(f"Platform {platform} failed with exception", 
                           job_id=job_id, platform=platform, error=str(result))
                platforms_failed += 1
            else:
                all_videos.extend(result)
                if result:  # If we got videos, count as success
                    platforms_success += 1
                else:  # Empty result still counts as attempted
                    platforms_success += 1
        
        # Log summary
        logger.info("platform.search.summary", extra={
            "job_id": job_id,
            "platforms_attempted": platforms_attempted,
            "platforms_success": platforms_success,
            "platforms_failed": platforms_failed,
            "total_videos": len(all_videos)
        })
        
        return all_videos
