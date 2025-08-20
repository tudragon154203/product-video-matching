import os
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
        video_id = video['video_id']
        uploader = sanitize_filename(video['uploader'])
        title = sanitize_filename(video['title'])
        
        # Create uploader directory
        uploader_dir = Path(download_dir) / uploader
        uploader_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if file already exists
        existing_files = list(uploader_dir.glob(f"{title}.*"))
        if existing_files:
            # Use existing file
            existing_file = existing_files[0]
            video['local_path'] = str(existing_file.absolute())
            logger.info(f"Using existing file: {existing_file}")
            return video
        
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
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video['url']])
                
                # Find the downloaded file
                downloaded_files = list(uploader_dir.glob(f"{title}.*"))
                if downloaded_files:
                    video['local_path'] = str(downloaded_files[0].absolute())
                    logger.info(f"Downloaded video: {video['title']}")
                    return video
                else:
                    logger.error(f"Downloaded file not found for video: {video['title']}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to download video {video['video_id']}: {str(e)}")
            # Log available formats for debugging
            try:
                with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                    info = ydl.extract_info(video['url'], download=False)
                    formats = info.get('formats', [])
                    logger.debug(f"Available formats for {video['video_id']}: {[f.get('format_id', '') for f in formats]}")
            except Exception as debug_e:
                logger.debug(f"Could not retrieve formats for debugging: {debug_e}")
            return None
