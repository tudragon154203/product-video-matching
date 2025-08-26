import time
import asyncio
import yt_dlp
from typing import Dict, Any
from common_py.logging_config import configure_logging
from .config import DownloaderConfig
from .retry_handler import RetryHandler
from .file_manager import FileManager
from .ytdlp_config import YTDLPOptionsBuilder

logger = configure_logging("video-crawler")

class YoutubeDownloader:
    """Main YouTube downloader class"""
    
    def __init__(self):
        self.config = DownloaderConfig()
        self.retry_handler = RetryHandler()
        self.file_manager = FileManager()
    
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
        
        try:
            # Create uploader directory
            uploader_dir = self.file_manager.create_uploader_directory(download_dir, uploader)
            
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
        
        # Download the video with resilient format selection and retry mechanism
        for attempt in range(self.config.MAX_RETRIES):
            # Rotate user agent for each attempt to avoid detection
            user_agent = self.config.get_random_user_agent()
            
            # Get format selection based on attempt number
            format_selection = self.config.get_format_option(attempt)
            
            # Configure proxy - use SOCKS5 proxy on first attempt, no proxy on retries
            proxy_config = self.config.SOCKS_PROXY if attempt == 0 else None
            
            # Build yt-dlp options
            ydl_opts = YTDLPOptionsBuilder.build_options(user_agent, format_selection, proxy_config)
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
                    
                    # Find the downloaded file
                    downloaded_file_path = self.file_manager.find_downloaded_file(uploader_dir, title)
                    if downloaded_file_path:
                        # Check if the file is valid (not empty)
                        if not self.file_manager.validate_downloaded_file(downloaded_file_path):
                            logger.error(f"[DOWNLOAD-EMPTY] Video: {title} | Downloaded file is empty. Retrying...")
                            # Remove the empty file
                            self.file_manager.remove_file(downloaded_file_path)
                            
                            # Handle retry
                            if await self.retry_handler.handle_retry(video, title, attempt, self.config.MAX_RETRIES, "empty file"):
                                continue
                            else:
                                logger.error(f"[DOWNLOAD-FAILED-FINAL] Video: {title} | All {self.config.MAX_RETRIES} attempts failed. Skipping this video.")
                                return None
                        
                        video['local_path'] = downloaded_file_path
                        self.file_manager.log_download_success(title, downloaded_file_path, start_time)
                        return video
                    else:
                        duration = time.time() - start_time
                        logger.error(f"[DOWNLOAD-ERROR] Video: {title} | Duration: {duration:.2f}s | Downloaded file not found")
                        
                        # Handle retry
                        if await self.retry_handler.handle_retry(video, title, attempt, self.config.MAX_RETRIES, "file not found"):
                            continue
                        else:
                            logger.error(f"[DOWNLOAD-FAILED-FINAL] Video: {title} | All {self.config.MAX_RETRIES} attempts failed. Skipping this video.")
                            return None
                            
            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e)
                logger.error(f"[DOWNLOAD-FAILED] Video: {title} | Duration: {duration:.2f}s | Attempt {attempt+1} failed: {error_msg}")
                
                # Log available formats for debugging non-403 errors
                if "HTTP Error 403" not in error_msg and "403" not in error_msg:
                    try:
                        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                            info = ydl.extract_info(video['url'], download=False)
                            formats = info.get('formats', [])
                            logger.debug(f"Available formats for {video['video_id']}: {[f.get('format_id', '') for f in formats]}")
                    except Exception as debug_e:
                        logger.debug(f"Could not retrieve formats for debugging: {debug_e}")
                
                # Handle retry based on error type
                if await self.retry_handler.handle_retry(video, title, attempt, self.config.MAX_RETRIES, error_msg):
                    continue
                else:
                    logger.error(f"[DOWNLOAD-FAILED-FINAL] Video: {title} | All {self.config.MAX_RETRIES} attempts failed. Skipping this video.")
                    return None
                    
        return None