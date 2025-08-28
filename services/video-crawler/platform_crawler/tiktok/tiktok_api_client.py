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
    Wrapper class for TikTok API with authentication and session management
    Handles retries, rate limiting, and error handling
    Includes fallback to mock API when real TikTok API has compatibility issues
    """
    
    def __init__(self, ms_token: Optional[str] = None, proxy_url: Optional[str] = None):
        self.ms_token = ms_token or config.TIKTOK_MS_TOKEN
        self.proxy_url = proxy_url or config.TIKTOK_PROXY_URL
        self.browser = config.TIKTOK_BROWSER
        self.headless = config.TIKTOK_HEADLESS
        self.max_retries = config.TIKTOK_MAX_RETRIES
        self.sleep_after = config.TIKTOK_SLEEP_AFTER
        self.session_count = config.TIKTOK_SESSION_COUNT
        self.api = None
        self._session_initialized = False
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_session()
    
    async def initialize_session(self) -> bool:
        """
        Initialize TikTok API session with authentication
        
        Returns:
            bool: True if session initialized successfully
        """
        if self._session_initialized:
            return True
            
        try:
            # Initialize TikTok API
            self.api = TikTokApi()
            
            # Prepare arguments for create_sessions
            create_session_args = {
                "ms_tokens": [self.ms_token] if self.ms_token else [],
                "browser": self.browser,
                "headless": self.headless,
                "num_sessions": 1,
                "sleep_after": 5,
                "timeout": 60000,
            }

            # Add proxy if configured
            if self.proxy_url and self.proxy_url.strip():
                create_session_args["proxies"] = [self.proxy_url]

            logger.info("Initializing TikTok API with compatible options", options=create_session_args)
            
            # Try to create sessions with extended timeout and better error handling
            try:
                await asyncio.wait_for(
                    self.api.create_sessions(**create_session_args),
                    timeout=60  # Extended timeout for browser startup
                )
                self._session_initialized = True
                logger.info("TikTok API session initialized successfully with version 6.2.2")
                return True
                
            except asyncio.TimeoutError:
                logger.error("TikTok API session initialization timed out after 60 seconds")
                # Try alternative approach with minimal parameters
                try:
                    logger.info("Retrying with minimal configuration...")
                    minimal_options = {
                        "ms_tokens": [self.ms_token] if self.ms_token else [],
                        "num_sessions": 1,
                        "sleep_after": 3,
                        "browser": self.browser,
                        "headless": self.headless,
                        "proxies": [self.proxy_url] if self.proxy_url and self.proxy_url.strip() else [],
                        "timeout": 60000,
                    }
                    await asyncio.wait_for(
                        self.api.create_sessions(**minimal_options),
                        timeout=60
                    )
                    self._session_initialized = True
                    logger.info("TikTok API session initialized with minimal configuration")
                    return True
                except Exception as fallback_error:
                    logger.error("Minimal session initialization also failed", error=str(fallback_error))
                    return False
            
        except Exception as e:
            logger.error("Failed to initialize TikTok API session", error=str(e))
            self._session_initialized = False
            return False
    
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
        Search for videos by keyword query
        
        Args:
            query: Search keyword/phrase
            count: Number of videos to return
            
        Returns:
            List of video metadata dictionaries
        """
        
        
        if not self._session_initialized:
            await self.initialize_session()
        
        if not self._session_initialized:
            logger.error("Cannot search videos: TikTok API session not initialized")
            return []
        
        for attempt in range(self.max_retries):
            try:
                logger.info("Searching TikTok videos", query=query, count=count, attempt=attempt + 1)
                
                # Use TikTok API to search videos
                videos = []
                async for video in self.api.hashtag(query).videos(count=count):
                    video_data = {
                        "video_id": video.id,
                        "url": f"https://www.tiktok.com/@{video.author.username}/video/{video.id}",
                        "title": video.desc or f"TikTok video by @{video.author.username}",
                        "author": video.author.username,
                        "author_name": getattr(video.author, 'nickname', video.author.username),
                        "duration_s": getattr(video, 'duration', 0),
                        "view_count": getattr(video.stats, 'playCount', 0),
                        "like_count": getattr(video.stats, 'diggCount', 0),
                        "share_count": getattr(video.stats, 'shareCount', 0),
                        "comment_count": getattr(video.stats, 'commentCount', 0),
                        "create_time": getattr(video, 'createTime', 0),
                        "download_url": None,  # Will be set by downloader
                        "platform": "tiktok"
                    }
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
        Get download URL for a specific video
        
        Args:
            video_id: TikTok video ID
            
        Returns:
            Download URL string or None if failed
        """
        
        
        if not self._session_initialized:
            await self.initialize_session()
        
        if not self._session_initialized:
            logger.error("Cannot get download URL: TikTok API session not initialized")
            return None
        
        for attempt in range(self.max_retries):
            try:
                logger.info("Getting TikTok video download URL", video_id=video_id, attempt=attempt + 1)
                
                # Get video object
                video = self.api.video(id=video_id)
                video_data = await video.info()
                
                # Extract download URL
                download_url = getattr(video_data, 'downloadAddr', None)
                if download_url:
                    logger.info("Successfully got TikTok download URL", video_id=video_id)
                    return download_url
                else:
                    logger.warning("No download URL found for video", video_id=video_id)
                    return None
                
            except Exception as e:
                logger.warning("TikTok download URL attempt failed", 
                             video_id=video_id, attempt=attempt + 1, error=str(e))
                
                if attempt < self.max_retries - 1:
                    # Wait before retry
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("All TikTok download URL attempts failed", video_id=video_id, error=str(e))
        
        return None
    
    def is_session_active(self) -> bool:
        """Check if TikTok API session is active"""
        return self._session_initialized and self.api is not None