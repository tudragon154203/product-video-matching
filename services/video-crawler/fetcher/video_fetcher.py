from typing import List, Dict, Any, Optional
from platform_crawler.interface import PlatformCrawlerInterface
from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler")


class VideoFetcher:
    """Handles video search across multiple platforms using platform crawlers"""
    
    def __init__(self, platform_crawlers: Optional[Dict[str, PlatformCrawlerInterface]] = None):
        self.platform_crawlers = platform_crawlers or {}
    
    async def search_platform_videos(self, platform: str, queries: List[str], recency_days: int, download_dir: str, num_videos: int) -> List[Dict[str, Any]]:
        """
        Generic method to search videos on a specific platform
        """
        if platform not in self.platform_crawlers:
            logger.warning(f"Platform crawler not available for: {platform}")
            return []
        
        try:
            crawler = self.platform_crawlers[platform]
            videos = await crawler.search_and_download_videos(
                queries=queries,
                recency_days=recency_days,
                download_dir=download_dir,
                num_videos=num_videos
            )
            
            logger.info(f"Found {len(videos)} videos on {platform}",
                       platform=platform, video_count=len(videos))
            return videos
            
        except Exception as e:
            logger.error(f"Failed to search videos on {platform}",
                        platform=platform, error=str(e))
            return []