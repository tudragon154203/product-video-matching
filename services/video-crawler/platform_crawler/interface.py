from abc import ABC, abstractmethod
from typing import List, Dict, Any


class PlatformCrawlerInterface(ABC):
    """Abstract base class for platform-specific video crawlers"""

    @abstractmethod
    async def search_and_download_videos(
        self, queries: List[str], recency_days: int, download_dir: str, num_videos: int
    ) -> List[Dict[str, Any]]:
        """
        Search for videos on the platform and download them

        Args:
            queries: List of search queries
            recency_days: How many days back to search for videos
            download_dir: Directory path where videos should be saved
            num_videos: Maximum number of videos to return per query

        Returns:
            List of video metadata dictionaries with keys:
                - platform: Platform identifier (e.g., "youtube", "bilibili")
                - url: Video URL
                - title: Video title
                - duration_s: Video duration in seconds
                - video_id: Unique identifier for the video (platform-specific)
                - local_path: Full path to the downloaded video file
        """
        pass
