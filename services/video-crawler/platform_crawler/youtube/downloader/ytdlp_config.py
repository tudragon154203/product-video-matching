import random
from typing import Dict, Any
from .config import DownloaderConfig

class YTDLPOptionsBuilder:
    """Builds yt-dlp options for video downloads"""
    
    @staticmethod
    def build_options(user_agent: str, format_selection: str, proxy_config: str = None) -> Dict[str, Any]:
        """
        Build yt-dlp options
        
        Args:
            user_agent: User agent string
            format_selection: Format selection string
            proxy_config: Proxy configuration (optional)
            
        Returns:
            Dict[str, Any]: yt-dlp options
        """
        ydl_opts = {
            'format': format_selection,
            'outtmpl': '',  # Will be set per download
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
            
        return ydl_opts