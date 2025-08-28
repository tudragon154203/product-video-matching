import os
from typing import List, Dict, Any
from pathlib import Path
import asyncio
from datetime import datetime, timedelta
from platform_crawler.interface import PlatformCrawlerInterface


class MockPlatformCrawler(PlatformCrawlerInterface):
    """Mock platform crawler for testing purposes"""
    
    def __init__(self, platform_name: str = "mock"):
        self.platform_name = platform_name
    
    async def search_and_download_videos(self, queries: List[str], recency_days: int, download_dir: str, num_videos: int) -> List[Dict[str, Any]]:
        """
        Mock implementation that generates fake video data and creates dummy files
        
        Args:
            queries: List of search queries
            recency_days: How many days back to search for videos
            download_dir: Directory path where videos should be saved
            
        Returns:
            List of mock video metadata dictionaries
        """
        # Ensure download directory exists
        Path(download_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate mock videos
        mock_videos = []
        
        for i, query in enumerate(queries):
            # Create up to num_videos mock videos per query
            for j in range(min(num_videos, len(queries))):
                video_id = f"mock_{query}_{j}"
                video_filename = f"{video_id}.mp4"
                local_path = os.path.join(download_dir, video_filename)
                
                video = {
                    "platform": self.platform_name,
                    "url": f"https://{self.platform_name}.com/watch?v={video_id}",
                    "title": f"Mock {self.platform_name.capitalize()} Video: {query} #{j+1}",
                    "duration_s": 60 + (j * 30),  # 1-3 minutes
                    "video_id": video_id,
                    "local_path": local_path
                }
                
                mock_videos.append(video)
        
        return mock_videos
    