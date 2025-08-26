import os
import time
import asyncio
import random
from typing import Dict, Any
from pathlib import Path
import yt_dlp
from common_py.logging_config import configure_logging
from utils.youtube_utils import sanitize_filename

logger = configure_logging("video-crawler")

class YoutubeDownloader:
    def __init__(self):
        # Define user agents to rotate and avoid detection
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        ]
        
        # SOCKS5 proxy configuration
        self.socks_proxy = "socks5://localhost:1080"

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
        uploader = sanitize_filename(video['uploader'])
        title = sanitize_filename(video['title'])
        
        # Log download start with full info
        logger.info(f"[DOWNLOAD-START] Video: {title} (ID: {video_id}) | Uploader: {uploader}")
        
        try:
            # Create uploader directory
            uploader_dir = Path(download_dir) / uploader
            uploader_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if file already exists
            existing_files = list(uploader_dir.glob(f"{title}.*"))
            if existing_files:
                # Use existing file
                existing_file = existing_files[0]
                video['local_path'] = str(existing_file.absolute())
                duration = time.time() - start_time
                logger.info(f"[DOWNLOAD-SKIP] Video: {title} | Duration: {duration:.2f}s | File already exists at: {existing_file}")
                return video
        
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[DIRECTORY-ERROR] Video: {title} | Duration: {duration:.2f}s | Error creating directory: {str(e)}")
            return None
        
        # Download the video with resilient format selection and retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            # Rotate user agent for each attempt to avoid detection
            user_agent = random.choice(self.user_agents)
            
            # Try different format selections to handle various video types
            format_options = [
                'bv*[height<=?1080][ext=mp4]+ba[ext=m4a]/b[height<=?1080][ext=mp4]/bv*[height<=?1080]+ba/b[height<=?1080]/best',
                'best[height<=?1080][ext=mp4]/best[height<=?1080]/best',
                'worst[height>=?360][ext=mp4]/worst[height>=?360]/worst',
            ]
            
            # Cycle through format options based on attempt number
            format_selection = format_options[attempt % len(format_options)]
            
            # Configure proxy - use SOCKS5 proxy on first attempt, no proxy on retries
            proxy_config = self.socks_proxy if attempt == 0 else None
            
            ydl_opts = {
                'format': format_selection,
                'outtmpl': str(uploader_dir / f"{title}.%(ext)s"),
                'quiet': True,
                'no_warnings': False,  # Changed to see warnings
                'nocheckcertificate': True,
                'merge_output_format': 'mp4',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'user_agent': user_agent,
                'http_headers': {
                    'User-Agent': user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                },
                'sleep_interval': 1,  # Add delay between requests
                'max_sleep_interval': 3,
                'socket_timeout': 30,  # Increase timeout
                'retries': 3,  # Retry on network errors
            }
            
            # Add proxy configuration if specified
            if proxy_config:
                ydl_opts['proxy'] = proxy_config
                logger.info(f"[DOWNLOAD-PROXY] Using proxy: {proxy_config}")
            
            try:
                # Run yt_dlp in a separate thread to avoid blocking the event loop
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    proxy_info = f" with proxy {proxy_config}" if proxy_config else " without proxy"
                    logger.info(f"[DOWNLOAD-BEGIN] Video: {title} | Attempt {attempt+1}/{max_retries} | Using user agent: {user_agent[:50]}... | Format: {format_selection}{proxy_info}")
                    await asyncio.to_thread(ydl.download, [video['url']])
                    logger.info(f"[DOWNLOAD-FINISH] Video: {title} | yt-dlp download completed")
                    
                    # Find the downloaded file
                    downloaded_files = list(uploader_dir.glob(f"{title}.*"))
                    if downloaded_files:
                        # Check if the file is valid (not empty)
                        downloaded_file = downloaded_files[0]
                        if downloaded_file.stat().st_size == 0:
                            logger.error(f"[DOWNLOAD-EMPTY] Video: {title} | Downloaded file is empty. Retrying...")
                            # Remove the empty file
                            downloaded_file.unlink()
                            if attempt < max_retries - 1:
                                # Wait before retrying
                                wait_time = 5 * (attempt + 1)  # Longer wait for empty files
                                logger.info(f"[DOWNLOAD-EMPTY-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2}")
                                await asyncio.sleep(wait_time)
                            continue
                        
                        file_path = str(downloaded_file.absolute())
                        video['local_path'] = file_path
                        duration = time.time() - start_time
                        file_size = downloaded_file.stat().st_size / (1024 * 1024)  # Size in MB
                        logger.info(f"[DOWNLOAD-SUCCESS] Video: {title} | Duration: {duration:.2f}s | Size: {file_size:.2f}MB | Path: {file_path}")
                        return video
                    else:
                        duration = time.time() - start_time
                        logger.error(f"[DOWNLOAD-ERROR] Video: {title} | Duration: {duration:.2f}s | Downloaded file not found")
                        if attempt < max_retries - 1:
                            # Wait before retrying
                            wait_time = 2 ** attempt  # Exponential backoff
                            logger.info(f"[DOWNLOAD-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2}")
                            await asyncio.sleep(wait_time)
                        continue
                        
            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e)
                logger.error(f"[DOWNLOAD-FAILED] Video: {title} | Duration: {duration:.2f}s | Attempt {attempt+1} failed: {error_msg}")
                
                # Check if it's a 403 error and handle it specifically
                if "HTTP Error 403" in error_msg or "403" in error_msg:
                    logger.warning(f"[DOWNLOAD-403] Video: {title} | HTTP 403 Forbidden error detected")
                    if attempt < max_retries - 1:
                        # Wait longer for 403 errors
                        wait_time = 10 * (attempt + 1)  # Increase wait time for 403 errors
                        logger.info(f"[DOWNLOAD-403-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2} due to 403 error")
                        await asyncio.sleep(wait_time)
                        continue
                elif "HTTP Error 429" in error_msg or "429" in error_msg or "Too Many Requests" in error_msg:
                    logger.warning(f"[DOWNLOAD-429] Video: {title} | HTTP 429 Too Many Requests error detected")
                    if attempt < max_retries - 1:
                        # Wait even longer for 429 errors
                        wait_time = 15 * (attempt + 1)
                        logger.info(f"[DOWNLOAD-429-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2} due to 429 error")
                        await asyncio.sleep(wait_time)
                        continue
                elif "empty" in error_msg.lower() or "empty file" in error_msg.lower():
                    logger.warning(f"[DOWNLOAD-EMPTY-ERROR] Video: {title} | Empty file error detected")
                    # Try a different format on next attempt
                    if attempt < max_retries - 1:
                        wait_time = 5 * (attempt + 1)
                        logger.info(f"[DOWNLOAD-EMPTY-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2} with different format")
                        await asyncio.sleep(wait_time)
                        continue
                elif "proxy" in error_msg.lower() or "connection" in error_msg.lower():
                    logger.warning(f"[DOWNLOAD-PROXY-ERROR] Video: {title} | Proxy/connection error detected")
                    # Try without proxy on next attempt
                    if attempt < max_retries - 1:
                        wait_time = 5 * (attempt + 1)
                        logger.info(f"[DOWNLOAD-PROXY-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2} without proxy")
                        await asyncio.sleep(wait_time)
                        continue
                else:
                    # Log available formats for debugging non-403 errors
                    try:
                        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                            info = ydl.extract_info(video['url'], download=False)
                            formats = info.get('formats', [])
                            logger.debug(f"Available formats for {video['video_id']}: {[f.get('format_id', '') for f in formats]}")
                    except Exception as debug_e:
                        logger.debug(f"Could not retrieve formats for debugging: {debug_e}")
                
                # If this was the last attempt, return None
                if attempt == max_retries - 1:
                    logger.error(f"[DOWNLOAD-FAILED-FINAL] Video: {title} | All {max_retries} attempts failed. Skipping this video.")
                    return None
                    
        return None