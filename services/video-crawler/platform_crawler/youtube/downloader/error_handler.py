import asyncio
import yt_dlp
from typing import Dict, Any
from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler:error_handler")


class ErrorHandler:
    """Handles error logging and debugging for YouTube downloads"""
    
    @staticmethod
    async def log_formats_for_debugging(video_url: str, video_id: str):
        """
        Log available formats for debugging purposes
        
        Args:
            video_url: URL of the video
            video_id: ID of the video
        """
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(video_url, download=False)
                formats = info.get('formats', [])
                logger.debug(f"Available formats for {video_id}: {[f.get('format_id', '') for f in formats]}")
        except Exception as debug_e:
            logger.debug(f"Could not retrieve formats for debugging: {debug_e}")
    
    @staticmethod
    def determine_wait_time(error_msg: str, attempt: int) -> int:
        """
        Determine appropriate wait time based on error type
        
        Args:
            error_msg: Error message
            attempt: Current attempt number
            
        Returns:
            Wait time in seconds
        """
        if "HTTP Error 403" in error_msg or "403" in error_msg:
            return min(10 * (attempt + 1), 300)  # Up to 5 minutes, capped
        elif "HTTP Error 429" in error_msg or "429" in error_msg or "Too Many Requests" in error_msg:
            return min(15 * (attempt + 1), 600)  # Up to 10 minutes, capped
        elif "empty" in error_msg.lower() or "empty file" in error_msg.lower():
            return min(5 * (attempt + 1), 150)  # Up to 2.5 minutes, capped
        elif "proxy" in error_msg.lower() or "connection" in error_msg.lower():
            return min(5 * (attempt + 1), 150)  # Up to 2.5 minutes, capped
        else:
            # Generic retry with exponential backoff, capped at 5 minutes
            return min(2 ** attempt, 300)  # Cap at 5 minutes
