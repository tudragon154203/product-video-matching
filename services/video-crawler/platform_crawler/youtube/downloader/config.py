import random

class DownloaderConfig:
    """Configuration for the YouTube downloader"""
    
    # User agents to rotate and avoid detection
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
    ]
    
    # SOCKS5 proxy configuration
    SOCKS_PROXY = "socks5://localhost:1080"
    
    # Maximum number of download retries
    MAX_RETRIES = 3
    
    # Format options for video download
    FORMAT_OPTIONS = [
        'bv*[height<=?1080][ext=mp4]+ba[ext=m4a]/b[height<=?1080][ext=mp4]/bv*[height<=?1080]+ba/b[height<=?1080]/best',
        'best[height<=?1080][ext=mp4]/best[height<=?1080]/best',
        'worst[height>=?360][ext=mp4]/worst[height>=?360]/worst',
    ]
    
    @classmethod
    def get_random_user_agent(cls):
        """Get a random user agent from the list"""
        return random.choice(cls.USER_AGENTS)
    
    @classmethod
    def get_format_option(cls, attempt):
        """Get format option based on attempt number"""
        return cls.FORMAT_OPTIONS[attempt % len(cls.FORMAT_OPTIONS)]