import os
import time
import asyncio
from typing import Dict, Any
from pathlib import Path
import yt_dlp
from common_py.logging_config import configure_logging
from utils.youtube_utils import sanitize_filename

logger = configure_logging("video-crawler")

class YoutubeDownloader:
    def __init__(self):
        pass

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
        
        # Download the video with resilient format selection
        ydl_opts = {
            'format': 'bv*[height<=?1080][ext=mp4]+ba[ext=m4a]/b[height<=?1080][ext=mp4]/bv*[height<=?1080]+ba/b[height<=?1080]/best',
            'outtmpl': str(uploader_dir / f"{title}.%(ext)s"),
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }
        
        # Download the video with resilient format selection
        ydl_opts = {
            'format': 'bv*[height<=?1080][ext=mp4]+ba[ext=m4a]/b[height<=?1080][ext=mp4]/bv*[height<=?1080]+ba/b[height<=?1080]/best',
            'outtmpl': str(uploader_dir / f"{title}.%(ext)s"),
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }
        
        try:
            # Run yt_dlp in a separate thread to avoid blocking the event loop
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"[DOWNLOAD-BEGIN] Video: {title} | Starting yt-dlp download in separate thread")
                await asyncio.to_thread(ydl.download, [video['url']])
                logger.info(f"[DOWNLOAD-FINISH] Video: {title} | yt-dlp download completed")
                
                # Find the downloaded file
                downloaded_files = list(uploader_dir.glob(f"{title}.*"))
                if downloaded_files:
                    file_path = str(downloaded_files[0].absolute())
                    video['local_path'] = file_path
                    duration = time.time() - start_time
                    file_size = downloaded_files[0].stat().st_size / (1024 * 1024)  # Size in MB
                    logger.info(f"[DOWNLOAD-SUCCESS] Video: {title} | Duration: {duration:.2f}s | Size: {file_size:.2f}MB | Path: {file_path}")
                    return video
                else:
                    duration = time.time() - start_time
                    logger.error(f"[DOWNLOAD-ERROR] Video: {title} | Duration: {duration:.2f}s | Downloaded file not found")
                    return None
                    
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[DOWNLOAD-FAILED] Video: {title} | Duration: {duration:.2f}s | Error: {str(e)}")
            # Log available formats for debugging
            try:
                with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                    info = ydl.extract_info(video['url'], download=False)
                    formats = info.get('formats', [])
                    logger.debug(f"Available formats for {video['video_id']}: {[f.get('format_id', '') for f in formats]}")
            except Exception as debug_e:
                logger.debug(f"Could not retrieve formats for debugging: {debug_e}")
            return None
