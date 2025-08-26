import random
from typing import Dict, Any
from .config import DownloaderConfig

class YTDLPOptionsBuilder:
    """Builds yt-dlp options for video downloads"""
    
    @staticmethod
    def build_options(user_agent: str, format_selection: str, proxy_config: str = None) -> Dict[str, Any]:
        """
        Build yt-dlp options with enhanced reliability settings
        
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
            # Enhanced reliability settings
            'socket_timeout': 60,  # Increased timeout for slow connections
            'retries': 10,  # More retries for transient errors
            'fragment_retries': 10,  # More retries for fragment downloads
            'file_access_retries': 5,  # More retries for file access errors
            'retry_sleep': 'http:exp=1:300',  # Exponential backoff for HTTP errors, up to 300 seconds
            'sleep_interval': 1,  # Add delay between requests
            'max_sleep_interval': 5,  # Increase max sleep interval
            'sleep_requests': 1,  # Sleep between requests during data extraction
            # Additional reliability options
            'throttled_rate': '100K',  # Minimum download rate before re-extracting
            'buffersize': 10240,  # Larger buffer size (10KB)
            'noresizebuffer': False,  # Allow automatic buffer resizing
            'http_chunk_size': 10485760,  # 10MB chunks for bypassing throttling
            'concurrent_fragment_downloads': 3,  # Concurrent fragment downloads
        }
        
        # Add proxy configuration if specified
        if proxy_config:
            ydl_opts['proxy'] = proxy_config
            
        return ydl_opts