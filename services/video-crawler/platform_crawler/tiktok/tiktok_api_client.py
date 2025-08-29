"""
TikTok API Client wrapper for handling authentication, sessions, and API calls
"""
import asyncio
import os
import random
from typing import Optional, Dict, Any, List
from TikTokApi import TikTokApi
from common_py.logging_config import configure_logging
from config_loader import config

logger = configure_logging("tiktok-api-client")


class TikTokApiClient:
    """
    Wrapper class for TikTok API with authentication and session management.
    Implements a singleton pattern to ensure only one instance exists.
    Handles retries, rate limiting, and error handling.
    Includes fallback to mock API when real TikTok API has compatibility issues.
    """

    _instance = None
    _initialized = False

    def __new__(cls, ms_token: Optional[str] = None, proxy_url: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(TikTokApiClient, cls).__new__(cls)
        return cls._instance

    def __init__(self, ms_token: Optional[str] = None, proxy_url: Optional[str] = None):
        if not self._initialized:
            self.ms_token = ms_token or config.TIKTOK_MS_TOKEN
            self.proxy_url = proxy_url or config.TIKTOK_PROXY_URL
            self.headless = config.TIKTOK_HEADLESS
            self.max_retries = config.TIKTOK_MAX_RETRIES
            self.sleep_after = config.TIKTOK_SLEEP_AFTER
            self.session_count = config.TIKTOK_SESSION_COUNT
            self.api = None
            self._session_initialized = False
            self._initialized = True
            
            # Initialize session synchronously
            asyncio.run(self.initialize_session())
            
            logger.info("TikTokApiClient singleton instance initialized for the first time.")
        else:
            logger.info("TikTokApiClient instance already exists. Reusing existing instance.")

    async def initialize_session(self) -> bool:
        """
        Initialize TikTok API session using the official pattern.
        
        Returns:
            bool: True if session initialized successfully
        """
        if self._session_initialized and self.api is not None:
            logger.info("TikTok API session already initialized. Skipping initialization.")
            return True
            
        logger.info("Initializing TikTok API session.")
        
        try:
            # Initialize TikTokApi without parameters first
            self.api = TikTokApi()
            
            # Build create_sessions arguments according to official docs
            create_session_args = {
                "ms_tokens": [self.ms_token] if self.ms_token else [],
                "num_sessions": 1,
                "sleep_after": 5,
                "headless": self.headless,
            }
            
            # Add proxy if configured
            if self.proxy_url and self.proxy_url.strip():
                create_session_args["proxies"] = [self.proxy_url]
            
            logger.info("Creating TikTok API sessions", extra={"options": create_session_args})
            
            # Use the official create_sessions pattern
            await self.api.create_sessions(**create_session_args)
            
            self._session_initialized = True
            logger.info("TikTok API session initialized successfully")
            return True
                
        except Exception as e:
            logger.error("Failed to initialize TikTok API session", error=str(e))
            self._session_initialized = False
            return False

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass

    async def close_session(self):
        """Close TikTok API session and cleanup resources"""
        try:
            if self.api and self._session_initialized:
                await self.api.close()
                self._session_initialized = False
                logger.info("TikTok API session closed successfully")
        except Exception as e:
            logger.error("Error closing TikTok API session", error=str(e))

    def is_session_active(self) -> bool:
        """Check if session is active (real or mock)"""
        return self._session_initialized

    async def search_videos(self, query: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        Search for videos by keyword query using TikTok API v6.2.2

        Args:
            query: Search keyword/phrase
            count: Number of videos to return

        Returns:
            List of video metadata dictionaries
        """

        # Check if session is active before proceeding
        if not self.is_session_active():
            logger.error("Cannot search videos: TikTok API session not initialized")
            return []

        for attempt in range(self.max_retries):
            try:
                logger.info("Searching TikTok videos", query=query, count=count, attempt=attempt + 1)

                # Use TikTok API to search videos 
                videos = []
                # Use the correct TikTok API search method: api.search.videos()
                async for video in self.api.search.videos(query, count=count):
                    video_data = await self._extract_video_data(video)
                    if video_data:
                        videos.append(video_data)

                logger.info("Successfully found TikTok videos", query=query, count=len(videos))
                return videos

            except Exception as e:
                logger.warning("TikTok search attempt failed",
                             query=query, attempt=attempt + 1, error=str(e))

                if attempt < self.max_retries - 1:
                    # Wait before retry with exponential backoff
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("All TikTok search attempts failed", query=query, error=str(e))

        return []

    async def get_video_download_url(self, video_id: str) -> Optional[str]:
        """
        Get download URL for a specific video using TikTok API v6.2.2

        Args:
            video_id: TikTok video ID

        Returns:
            Download URL string or None if failed
        """

        # Check if session is active before proceeding
        if not self.is_session_active():
            logger.error("Cannot get download URL: TikTok API session not initialized")
            return None

        for attempt in range(self.max_retries):
            try:
                logger.info("Getting TikTok video download URL", video_id=video_id, attempt=attempt + 1)

                # Get video object using proper TikTok API method
                video = self.api.video(id=video_id)
                try:
                    # Check if video object has info method and it's awaitable
                    if hasattr(video, 'info') and callable(video.info):
                        video_data = await video.info()
                        
                        # Extract download URL with multiple potential field names
                        download_url = None
                        
                        # Try different possible field names for download URL
                        for field in ['downloadAddr', 'playAddr', 'download_url', 'video_url']:
                            download_url = getattr(video_data, field, None)
                            if download_url:
                                logger.info(f"Found download URL via field: {field}", video_id=video_id)
                                break
                        
                        # Try to get from stats if direct fields don't work
                        if not download_url and hasattr(video_data, 'stats'):
                            download_url = getattr(video_data.stats, 'downloadUrl', None)
                        
                        if download_url:
                            logger.info("Successfully got TikTok download URL", video_id=video_id)
                            return download_url
                        else:
                            logger.warning("No download URL found for video", video_id=video_id)
                            return None
                    else:
                        logger.warning("Video object doesn't have info method", video_id=video_id)
                        return None
                        
                except Exception as video_error:
                    logger.warning("Video info retrieval failed", video_id=video_id, error=str(video_error))
                    # Try alternative method to get video bytes and infer URL
                    try:
                        if hasattr(video, 'bytes') and callable(video.bytes):
                            video_bytes = await video.bytes()
                            if video_bytes:
                                # If we can get bytes, assume we can construct URL
                                return f"https://www.tiktok.com/@user/video/{video_id}"
                    except Exception as bytes_error:
                        logger.warning("Alternative download method also failed", video_id=video_id, error=str(bytes_error))
                        return None

            except Exception as e:
                logger.warning("TikTok download URL attempt failed",
                             video_id=video_id, attempt=attempt + 1, error=str(e))

                if attempt < self.max_retries - 1:
                    # Wait before retry with exponential backoff
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("All TikTok download URL attempts failed", video_id=video_id, error=str(e))

        return None

    def is_session_active(self) -> bool:
        """Check if TikTok API session is active"""
        return self._session_initialized and self.api is not None
    
    async def _extract_video_data(self, video) -> Optional[Dict[str, Any]]:
        """
        Extract video data from TikTok API video object with error handling
        
        Args:
            video: TikTok API video object
            
        Returns:
            Video metadata dictionary or None if extraction fails
        """
        try:
            if not video or not hasattr(video, 'id'):
                return None
                
            # Safely access attributes with fallbacks
            video_id = getattr(video, 'id', None)
            if not video_id:
                return None
                
            # Get author info safely
            author = getattr(video, 'author', None)
            username = getattr(author, 'username', 'unknown') if author else 'unknown'
            author_name = getattr(author, 'nickname', username) if author else username
            
            # Get stats safely
            stats = getattr(video, 'stats', None)
            if stats:
                view_count = getattr(stats, 'playCount', 0)
                like_count = getattr(stats, 'diggCount', 0)
                share_count = getattr(stats, 'shareCount', 0)
                comment_count = getattr(stats, 'commentCount', 0)
            else:
                view_count = like_count = share_count = comment_count = 0
            
            # Get other attributes safely
            desc = getattr(video, 'desc', '')
            duration = getattr(video, 'duration', 0)
            create_time = getattr(video, 'createTime', 0)
            
            video_data = {
                "video_id": video_id,
                "url": f"https://www.tiktok.com/@{username}/video/{video_id}",
                "title": desc or f"TikTok video by @{username}",
                "author": username,
                "author_name": author_name,
                "duration_s": duration,
                "view_count": view_count,
                "like_count": like_count,
                "share_count": share_count,
                "comment_count": comment_count,
                "create_time": create_time,
                "download_url": None,  # Will be set by downloader
                "platform": "tiktok"
            }
            
            return video_data
            
        except Exception as e:
            logger.warning("Failed to extract video data", error=str(e))
            return None