"""
TikTok Video Downloader with support for downloading videos without watermarks
"""
import os
import asyncio
import aiohttp
import aiofiles
from typing import Dict, Any, Optional
from pathlib import Path
from urllib.parse import urlparse
from common_py.logging_config import configure_logging
from .tiktok_api_client import TikTokApiClient
from config_loader import config

logger = configure_logging("tiktok-downloader")


class TikTokDownloader:
    """
    TikTok video downloader with watermark removal and file management
    """
    
    def __init__(self):
        self.session = None
        self.api_client = None
        self.max_retries = config.TIKTOK_MAX_RETRIES
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._initialize_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._cleanup_session()
    
    async def _initialize_session(self):
        """Initialize HTTP session and TikTok API client"""
        try:
            # Create aiohttp session with timeout
            timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes timeout
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # Initialize TikTok API client
            self.api_client = TikTokApiClient()
            await self.api_client.initialize_session()
            
            logger.info("TikTok downloader session initialized")
        except Exception as e:
            logger.error("Failed to initialize TikTok downloader session", error=str(e))
            raise
    
    async def _cleanup_session(self):
        """Cleanup HTTP session and API client"""
        try:
            if self.session:
                await self.session.close()
            if self.api_client:
                await self.api_client.close_session()
            logger.info("TikTok downloader session cleaned up")
        except Exception as e:
            logger.error("Error cleaning up TikTok downloader session", error=str(e))
    
    async def download_video(
        self, 
        video_data: Dict[str, Any], 
        download_dir: str
    ) -> Optional[str]:
        """
        Download a TikTok video to local storage
        
        Args:
            video_data: Video metadata dictionary with video_id, url, title, etc.
            download_dir: Directory to save the downloaded video
            
        Returns:
            Local file path of downloaded video or None if failed
        """
        video_id = video_data.get('video_id')
        video_url = video_data.get('url')
        title = video_data.get('title', 'tiktok_video')
        
        if not video_id or not video_url:
            logger.error("Missing video_id or url in video data", video_data=video_data)
            return None
        
        try:
            # Ensure download directory exists
            Path(download_dir).mkdir(parents=True, exist_ok=True)
            
            # Generate safe filename
            safe_filename = self._generate_safe_filename(video_id, title)
            local_path = os.path.join(download_dir, safe_filename)
            
            # Check if file already exists
            if os.path.exists(local_path):
                logger.info("Video already downloaded", video_id=video_id, local_path=local_path)
                return local_path
            
            logger.info("Starting TikTok video download", video_id=video_id, url=video_url)
            
            # Get download URL using TikTok API
            download_url = await self._get_download_url(video_data)
            
            if not download_url:
                logger.error("Failed to get download URL", video_id=video_id)
                return None
            
            # Download the video file
            success = await self._download_file(download_url, local_path)
            
            if success:
                logger.info("Successfully downloaded TikTok video", 
                           video_id=video_id, local_path=local_path)
                return local_path
            else:
                logger.error("Failed to download TikTok video", video_id=video_id)
                return None
                
        except Exception as e:
            logger.error("Error downloading TikTok video", video_id=video_id, error=str(e))
            return None
    
    async def _get_download_url(self, video_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the actual download URL for the video
        
        Args:
            video_data: Video metadata dictionary
            
        Returns:
            Download URL string or None if failed
        """
        video_id = video_data.get('video_id')
        
        try:
            # First try to get download URL from API client
            if self.api_client:
                download_url = await self.api_client.get_video_download_url(video_id)
                if download_url:
                    return download_url
            
            # Fallback: try to extract from video data
            if 'download_url' in video_data and video_data['download_url']:
                return video_data['download_url']
            
            # Last resort: use the main video URL (may have watermark)
            video_url = video_data.get('url')
            if video_url:
                logger.warning("Using main video URL as fallback (may have watermark)", 
                             video_id=video_id)
                return video_url
            
            return None
            
        except Exception as e:
            logger.error("Error getting download URL", video_id=video_id, error=str(e))
            return None
    
    async def _download_file(self, download_url: str, local_path: str) -> bool:
        """
        Download file from URL to local path
        
        Args:
            download_url: URL to download from
            local_path: Local file path to save to
            
        Returns:
            True if download successful, False otherwise
        """
        for attempt in range(self.max_retries):
            try:
                logger.info("Downloading file", url=download_url, attempt=attempt + 1)
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Referer': 'https://www.tiktok.com/',
                }
                
                async with self.session.get(download_url, headers=headers) as response:
                    if response.status == 200:
                        # Create temporary file first
                        temp_path = local_path + '.tmp'
                        
                        async with aiofiles.open(temp_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        
                        # Move temp file to final location
                        os.rename(temp_path, local_path)
                        
                        logger.info("File downloaded successfully", local_path=local_path)
                        return True
                    else:
                        logger.warning("HTTP error downloading file", 
                                     status=response.status, attempt=attempt + 1)
                        
            except Exception as e:
                logger.warning("Download attempt failed", 
                             attempt=attempt + 1, error=str(e))
                
                # Clean up temp file if it exists
                temp_path = local_path + '.tmp'
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
            
            # Wait before retry
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)
        
        logger.error("All download attempts failed", url=download_url)
        return False
    
    def _generate_safe_filename(self, video_id: str, title: str) -> str:
        """
        Generate a safe filename for the video
        
        Args:
            video_id: TikTok video ID
            title: Video title
            
        Returns:
            Safe filename string
        """
        # Clean title for use in filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
        
        if not safe_title:
            safe_title = "tiktok_video"
        
        # Create filename with video ID and safe title
        filename = f"{video_id}_{safe_title}.mp4"
        
        return filename
    
    async def download_multiple_videos(
        self, 
        videos: list[Dict[str, Any]], 
        download_dir: str,
        max_concurrent: int = 3
    ) -> list[Dict[str, Any]]:
        """
        Download multiple videos concurrently
        
        Args:
            videos: List of video metadata dictionaries
            download_dir: Directory to save downloaded videos
            max_concurrent: Maximum number of concurrent downloads
            
        Returns:
            List of video metadata with local_path added
        """
        if not videos:
            return []
        
        logger.info("Starting batch download of TikTok videos", 
                   count=len(videos), max_concurrent=max_concurrent)
        
        # Create semaphore to limit concurrent downloads
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_single(video_data):
            async with semaphore:
                local_path = await self.download_video(video_data, download_dir)
                if local_path:
                    video_data['local_path'] = local_path
                    return video_data
                return None
        
        # Execute downloads concurrently
        tasks = [download_single(video.copy()) for video in videos]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful downloads
        successful_downloads = []
        for result in results:
            if isinstance(result, dict) and result is not None:
                successful_downloads.append(result)
            elif isinstance(result, Exception):
                logger.error("Download task failed", error=str(result))
        
        logger.info("Completed batch download", 
                   total=len(videos), 
                   successful=len(successful_downloads))
        
        return successful_downloads
    
    def get_video_info(self, local_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a downloaded video file
        
        Args:
            local_path: Path to the video file
            
        Returns:
            Dictionary with file information or None if failed
        """
        try:
            if not os.path.exists(local_path):
                return None
            
            stat = os.stat(local_path)
            
            return {
                'file_size': stat.st_size,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'exists': True
            }
            
        except Exception as e:
            logger.error("Error getting video file info", local_path=local_path, error=str(e))
            return None