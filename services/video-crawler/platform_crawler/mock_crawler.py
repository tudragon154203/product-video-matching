import os
from pathlib import Path
from typing import Any, Dict, List

from platform_crawler.interface import PlatformCrawlerInterface


class MockPlatformCrawler(PlatformCrawlerInterface):
    """Mock platform crawler for testing purposes"""

    def __init__(self, platform_name: str = "mock"):
        self.platform_name = platform_name

    async def search_and_download_videos(
        self, queries: List[str], recency_days: int, download_dir: str, num_videos: int
    ) -> List[Dict[str, Any]]:
        """
        Mock implementation that generates deterministic fake video data and creates dummy files

        Args:
            queries: List of search queries
            recency_days: How many days back to search for videos
            download_dir: Directory path where videos should be saved

        Returns:
            List of mock video metadata dictionaries with existing local files
        """
        # Ensure download directory exists
        Path(download_dir).mkdir(parents=True, exist_ok=True)

        # Ensure we always return at least 2 items per request deterministically
        total_items = max(2, num_videos if num_videos and num_videos > 0 else 2)
        queries = queries or ["mock_query"]

        mock_videos: List[Dict[str, Any]] = []

        for j in range(total_items):
            qidx = j % len(queries)
            query = queries[qidx]
            video_id = f"mock_{self.platform_name}_{qidx}_{j}"
            video_filename = f"{video_id}.mp4"
            local_path = os.path.join(download_dir, video_filename)

            # Create small dummy media file to satisfy existence checks
            try:
                if not os.path.exists(local_path):
                    with open(local_path, "wb") as f:
                        f.write(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom")  # minimal MP4 header-ish bytes
            except Exception:
                # Fallback to a text file if filesystem blocks binary writes
                with open(local_path, "w", encoding="utf-8") as f:
                    f.write("DUMMY VIDEO CONTENT")

            video = {
                "platform": self.platform_name,
                "url": f"https://{self.platform_name}.example/watch?v={video_id}",
                "title": f"Mock {self.platform_name.capitalize()} Video: {query} #{j+1}",
                "duration_s": 30 + (j % 3) * 15,  # 30-60 seconds
                "video_id": video_id,
                "local_path": local_path,
            }

            mock_videos.append(video)

        return mock_videos
