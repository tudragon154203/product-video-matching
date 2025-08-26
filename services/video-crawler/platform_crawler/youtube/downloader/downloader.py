import time
import asyncio
import yt_dlp
from typing import Dict, Any
from common_py.logging_config import configure_logging
from .config import DownloaderConfig
from .retry_handler import RetryHandler
from .file_manager import FileManager
from .ytdlp_config import YTDLPOptionsBuilder
from .error_handler import ErrorHandler

logger = configure_logging("video-crawler")


class YoutubeDownloader:
    """Main YouTube downloader class"""
    
    def __init__(self):
        self.config = DownloaderConfig()
        self.retry_handler = RetryHandler()
        self.file_manager = FileManager()
        self.error_handler = ErrorHandler()
    
    async def download_video(self, video: Dict[str, Any], download_dir: str) -> Dict[str, Any]:
        """
        Download a single video to the specified directory
        
        Args:
            video: Video metadata dictionary
            download_dir: Base download directory
            
        Returns:
            Video metadata with local_path added, or None if download failed
        """
        start_time = time.time()
        video_id = video['video_id']
        uploader = video['uploader']
        title = video['title']
        
        # Log download start with full info
        logger.info(f"[DOWNLOAD-START] Video: {title} (ID: {video_id}) | Uploader: {uploader}")
        
        # Check if file already exists
        existing_result = await self._check_existing_file(video, download_dir, title, start_time)
        if existing_result:
            return existing_result
        
        # Download the video with resilient format selection and retry mechanism
        return await self._download_with_retries(video, download_dir, title, start_time)
    
    async def _check_existing_file(self, video: Dict[str, Any], download_dir: str, title: str, start_time: float) -> Dict[str, Any]:
        """
        Check if the video file already exists
        
        Args:
            video: Video metadata dictionary
            download_dir: Base download directory
            title: Video title
            start_time: Start time for logging
            
        Returns:
            Video metadata with local_path if file exists, None otherwise
        """
        try:
            # Create uploader directory
            uploader_dir = self.file_manager.create_uploader_directory(download_dir, video['uploader'])
            
            # Check if file already exists
            existing_file_path = self.file_manager.check_existing_file(uploader_dir, title)
            if existing_file_path:
                # Use existing file
                video['local_path'] = existing_file_path
                duration = time.time() - start_time
                logger.info(f"[DOWNLOAD-SKIP] Video: {title} | Duration: {duration:.2f}s | File already exists at: {existing_file_path}")
                return video
        
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[DIRECTORY-ERROR] Video: {title} | Duration: {duration:.2f}s | Error creating directory: {str(e)}")
            return None
            
        return None
    
    async def _download_with_retries(self, video: Dict[str, Any], download_dir: str, title: str, start_time: float) -> Dict[str, Any]:
        """
        Download the video with retry mechanism
        
        Args:
            video: Video metadata dictionary
            download_dir: Base download directory
            title: Video title
            start_time: Start time for logging
            
        Returns:
            Video metadata with local_path if successful, None otherwise
        """
        for attempt in range(self.config.MAX_RETRIES):
            # Rotate user agent for each attempt to avoid detection
            user_agent = self.config.get_random_user_agent()
            
            # Get format selection based on attempt number
            format_selection = self.config.get_format_option(attempt)
            
            # Configure proxy - use SOCKS5 proxy on first attempt, no proxy on retries
            proxy_config = self.config.SOCKS_PROXY if attempt == 0 else None
            
            # Build yt-dlp options
            ydl_opts = YTDLPOptionsBuilder.build_options(user_agent, format_selection, proxy_config)
            uploader_dir = self.file_manager.create_uploader_directory(download_dir, video['uploader'])
            ydl_opts['outtmpl'] = str(uploader_dir / f"{title}.%(ext)s")
            
            # Add proxy configuration info to log
            if proxy_config:
                logger.info(f"[DOWNLOAD-PROXY] Using proxy: {proxy_config}")
            
            try:
                # Run yt_dlp in a separate thread to avoid blocking the event loop
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    proxy_info = f" with proxy {proxy_config}" if proxy_config else " without proxy"
                    logger.info(f"[DOWNLOAD-BEGIN] Video: {title} | Attempt {attempt+1}/{self.config.MAX_RETRIES} | Using user agent: {user_agent[:50]}... | Format: {format_selection}{proxy_info}")
                    await asyncio.to_thread(ydl.download, [video['url']])
                    logger.info(f"[DOWNLOAD-FINISH] Video: {title} | yt-dlp download completed")
                    
                    # Process the downloaded file
                    return await self._process_downloaded_file(video, uploader_dir, title, start_time, attempt)
                            
            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e)
                logger.error(f"[DOWNLOAD-FAILED] Video: {title} | Duration: {duration:.2f}s | Attempt {attempt+1} failed: {error_msg}")
                
                # Handle the exception
                result = await self._handle_download_exception(video, title, attempt, error_msg)
                if result == "retry":
                    continue
                elif result == "fail":
                    return None
                    
        return None
    
    async def _process_downloaded_file(self, video: Dict[str, Any], uploader_dir: str, title: str, start_time: float, attempt: int) -> Dict[str, Any]:
        """
        Process the downloaded file
        
        Args:
            video: Video metadata dictionary
            uploader_dir: Uploader directory
            title: Video title
            start_time: Start time for logging
            attempt: Current attempt number
            
        Returns:
            Video metadata with local_path if successful, None otherwise
        """
        # Find the downloaded file
        downloaded_file_path = self.file_manager.find_downloaded_file(uploader_dir, title)
        if downloaded_file_path:
            # Check if the file is valid (not empty)
            if not self.file_manager.validate_downloaded_file(downloaded_file_path):
                logger.error(f"[DOWNLOAD-EMPTY] Video: {title} | Downloaded file is empty. Retrying...")
                # Remove the empty file
                self.file_manager.remove_file(downloaded_file_path)
                
                # Handle retry with exponential backoff
                wait_time = min(2 ** attempt, 300)  # Cap at 5 minutes
                if attempt < self.config.MAX_RETRIES - 1:
                    logger.info(f"[DOWNLOAD-EMPTY-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2}")
                    await asyncio.sleep(wait_time)
                    return None  # Will trigger a retry
                
            video['local_path'] = downloaded_file_path
            self.file_manager.log_download_success(title, downloaded_file_path, start_time)
            return video
        else:
            duration = time.time() - start_time
            logger.error(f"[DOWNLOAD-ERROR] Video: {title} | Duration: {duration:.2f}s | Downloaded file not found")
            
            # Handle retry with exponential backoff
            wait_time = min(2 ** attempt, 300)  # Cap at 5 minutes
            if attempt < self.config.MAX_RETRIES - 1:
                logger.info(f"[DOWNLOAD-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2}")
                await asyncio.sleep(wait_time)
                return None  # Will trigger a retry
                
        return None
    
    async def _handle_download_exception(self, video: Dict[str, Any], title: str, attempt: int, error_msg: str) -> str:
        """
        Handle download exceptions
        
        Args:
            video: Video metadata dictionary
            title: Video title
            attempt: Current attempt number
            error_msg: Error message
            
        Returns:
            String indicating action: "retry", "fail", or "continue"
        """
        # Log available formats for debugging non-403 errors
        if "HTTP Error 403" not in error_msg and "403" not in error_msg:
            await self.error_handler.log_formats_for_debugging(video['url'], video['video_id'])
        
        # Handle specific error types with appropriate wait times
        if "HTTP Error 403" in error_msg or "403" in error_msg:
            logger.warning(f"[DOWNLOAD-403] Video: {title} | HTTP 403 Forbidden error detected")
            wait_time = self.error_handler.determine_wait_time(error_msg, attempt)
            if attempt < self.config.MAX_RETRIES - 1:
                logger.info(f"[DOWNLOAD-403-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2} due to 403 error")
                await asyncio.sleep(wait_time)
                return "retry"
        elif "HTTP Error 429" in error_msg or "429" in error_msg or "Too Many Requests" in error_msg:
            logger.warning(f"[DOWNLOAD-429] Video: {title} | HTTP 429 Too Many Requests error detected")
            wait_time = self.error_handler.determine_wait_time(error_msg, attempt)
            if attempt < self.config.MAX_RETRIES - 1:
                logger.info(f"[DOWNLOAD-429-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2} due to 429 error")
                await asyncio.sleep(wait_time)
                return "retry"
        elif "empty" in error_msg.lower() or "empty file" in error_msg.lower():
            logger.warning(f"[DOWNLOAD-EMPTY-ERROR] Video: {title} | Empty file error detected")
            wait_time = self.error_handler.determine_wait_time(error_msg, attempt)
            if attempt < self.config.MAX_RETRIES - 1:
                logger.info(f"[DOWNLOAD-EMPTY-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2} with different format")
                await asyncio.sleep(wait_time)
                return "retry"
        elif "proxy" in error_msg.lower() or "connection" in error_msg.lower():
            logger.warning(f"[DOWNLOAD-PROXY-ERROR] Video: {title} | Proxy/connection error detected")
            wait_time = self.error_handler.determine_wait_time(error_msg, attempt)
            if attempt < self.config.MAX_RETRIES - 1:
                logger.info(f"[DOWNLOAD-PROXY-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2} without proxy")
                await asyncio.sleep(wait_time)
                return "retry"
        else:
            # Generic retry with exponential backoff
            wait_time = self.error_handler.determine_wait_time(error_msg, attempt)
            if attempt < self.config.MAX_RETRIES - 1:
                logger.info(f"[DOWNLOAD-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2}")
                await asyncio.sleep(wait_time)
                return "retry"
            
        # If we've exhausted all retries
        logger.error(f"[DOWNLOAD-FAILED-FINAL] Video: {title} | All {self.config.MAX_RETRIES} attempts failed. Skipping this video.")
        return "fail"