"""
Mock TikTok API client for testing when real TikTok API has issues
This provides a fallback for integration testing on macOS where TikTok API has compatibility issues
"""
import asyncio
import random
import time
from typing import List, Dict, Any, Optional
from common_py.logging_config import configure_logging

logger = configure_logging("mock-tiktok-api")


class MockTikTokApiClient:
    """
    Mock TikTok API client that simulates real TikTok API responses
    Used for testing when the real API has browser compatibility issues
    """
    
    def __init__(self, ms_token: Optional[str] = None, proxy_url: Optional[str] = None):
        self.ms_token = ms_token
        self.proxy_url = proxy_url
        self._session_initialized = True  # Mock always "succeeds"
        logger.info("Mock TikTok API client initialized for testing")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        logger.info("Mock TikTok API client session closed")
    
    async def initialize_session(self) -> bool:
        """Mock session initialization - always succeeds"""
        await asyncio.sleep(0.1)  # Simulate initialization delay
        self._session_initialized = True
        logger.info("Mock TikTok API session initialized successfully")
        return True
    
    async def close_session(self):
        """Mock session closing"""
        self._session_initialized = False
        logger.info("Mock TikTok API session closed")
    
    def is_session_initialized(self) -> bool:
        """Check if session is initialized"""
        return self._session_initialized
    
    async def search_videos(self, query: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        Mock video search - returns realistic fake data
        
        Args:
            query: Search keyword/phrase
            count: Number of videos to return
            
        Returns:
            List of mock video metadata dictionaries
        """
        await asyncio.sleep(0.2)  # Simulate network delay
        
        # Generate mock video data based on query
        videos = []
        for i in range(min(count, 5)):  # Limit to 5 for realistic response
            video_id = f"mock_{random.randint(1000000000, 9999999999)}"
            video_data = {
                "video_id": video_id,
                "url": f"https://www.tiktok.com/@mock_user_{i}/video/{video_id}",
                "title": f"Mock TikTok video about {query} - #{i+1}",
                "author": f"mock_user_{i}",
                "author_name": f"Mock User {i+1}",
                "duration_s": random.randint(15, 60),
                "view_count": random.randint(1000, 100000),
                "like_count": random.randint(50, 5000),
                "share_count": random.randint(10, 500),
                "comment_count": random.randint(5, 200),
                "create_time": time.time() - (i * 3600),  # Recent timestamps (decreasing by 1 hour per video)
                "download_url": f"https://mock.tiktok.com/video/{video_id}.mp4",
                "platform": "tiktok"
            }
            videos.append(video_data)
        
        logger.info("Mock TikTok search completed", query=query, count=len(videos))
        return videos
    
    async def get_video_download_url(self, video_id: str) -> Optional[str]:
        """
        Mock download URL retrieval
        
        Args:
            video_id: TikTok video ID
            
        Returns:
            Mock download URL
        """
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Return mock download URL
        download_url = f"https://mock.tiktok.com/download/{video_id}.mp4"
        logger.info("Mock TikTok download URL retrieved", video_id=video_id, url=download_url)
        return download_url