"""
TikTok utility functions and error handling
"""
import re
import time
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qs
from common_py.logging_config import configure_logging

logger = configure_logging("tiktok-utils")


class TikTokError(Exception):
    """Base exception for TikTok-related errors"""
    pass


class TikTokAuthError(TikTokError):
    """Exception for TikTok authentication errors"""
    pass


class TikTokRateLimitError(TikTokError):
    """Exception for TikTok rate limiting errors"""
    pass


class TikTokVideoNotFoundError(TikTokError):
    """Exception for when a TikTok video is not found or unavailable"""
    pass


class TikTokRegionBlockedError(TikTokError):
    """Exception for when TikTok content is blocked in a region"""
    pass


def extract_video_id_from_url(url: str) -> Optional[str]:
    """
    Extract TikTok video ID from various TikTok URL formats
    
    Args:
        url: TikTok video URL
        
    Returns:
        Video ID string or None if not found
    """
    if not url:
        return None
    
    try:
        # Common TikTok URL patterns
        patterns = [
            r'tiktok\.com/@[^/]+/video/(\d+)',
            r'vm\.tiktok\.com/([A-Za-z0-9]+)',
            r'tiktok\.com/t/([A-Za-z0-9]+)',
            r'/video/(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Try parsing as query parameter
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        if 'id' in query_params:
            return query_params['id'][0]
        
        logger.warning("Could not extract video ID from URL", url=url)
        return None
        
    except Exception as e:
        logger.error("Error extracting video ID from URL", url=url, error=str(e))
        return None


def is_valid_tiktok_url(url: str) -> bool:
    """
    Check if URL is a valid TikTok video URL
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid TikTok URL, False otherwise
    """
    if not url:
        return False
    
    try:
        tiktok_domains = [
            'tiktok.com',
            'vm.tiktok.com',
            'www.tiktok.com',
            'm.tiktok.com'
        ]
        
        parsed_url = urlparse(url)
        return any(domain in parsed_url.netloc for domain in tiktok_domains)
        
    except Exception:
        return False


def sanitize_search_query(query: str) -> str:
    """
    Sanitize search query for TikTok API
    
    Args:
        query: Raw search query
        
    Returns:
        Sanitized query string
    """
    if not query:
        return ""
    
    # Remove excessive whitespace
    query = re.sub(r'\s+', ' ', query.strip())
    
    # Remove special characters that might cause issues
    query = re.sub(r'[<>\"\'&]', '', query)
    
    # Limit length
    if len(query) > 100:
        query = query[:100]
    
    return query


def format_tiktok_hashtag(hashtag: str) -> str:
    """
    Format hashtag for TikTok search
    
    Args:
        hashtag: Raw hashtag string
        
    Returns:
        Formatted hashtag
    """
    if not hashtag:
        return ""
    
    # Remove # if present and clean up
    clean_hashtag = hashtag.lstrip('#').strip()
    
    # Remove spaces and special characters
    clean_hashtag = re.sub(r'[^a-zA-Z0-9_]', '', clean_hashtag)
    
    return clean_hashtag


def is_vietnamese_text(text: str) -> bool:
    """
    Check if text contains Vietnamese characters
    
    Args:
        text: Text to check
        
    Returns:
        True if text contains Vietnamese characters
    """
    if not text:
        return False
    
    # Vietnamese unicode ranges
    vietnamese_pattern = r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]'
    
    return bool(re.search(vietnamese_pattern, text.lower()))


def estimate_download_time(file_size_bytes: int, bandwidth_mbps: float = 10.0) -> float:
    """
    Estimate download time for a video file
    
    Args:
        file_size_bytes: File size in bytes
        bandwidth_mbps: Available bandwidth in Mbps
        
    Returns:
        Estimated download time in seconds
    """
    if file_size_bytes <= 0 or bandwidth_mbps <= 0:
        return 0.0
    
    # Convert Mbps to bytes per second
    bandwidth_bps = bandwidth_mbps * 1024 * 1024 / 8
    
    # Add 20% overhead for protocol overhead
    estimated_time = (file_size_bytes / bandwidth_bps) * 1.2
    
    return estimated_time


def handle_tiktok_error(error: Exception, context: str = "") -> TikTokError:
    """
    Convert generic exceptions to specific TikTok errors
    
    Args:
        error: Original exception
        context: Additional context about when the error occurred
        
    Returns:
        Appropriate TikTokError subclass
    """
    error_message = str(error).lower()
    
    if any(keyword in error_message for keyword in ['auth', 'token', 'login', 'session']):
        return TikTokAuthError(f"Authentication error{' in ' + context if context else ''}: {error}")
    
    elif any(keyword in error_message for keyword in ['rate limit', 'too many requests', '429']):
        return TikTokRateLimitError(f"Rate limit error{' in ' + context if context else ''}: {error}")
    
    elif any(keyword in error_message for keyword in ['not found', '404', 'video unavailable']):
        return TikTokVideoNotFoundError(f"Video not found{' in ' + context if context else ''}: {error}")
    
    elif any(keyword in error_message for keyword in ['region', 'blocked', 'geo', 'country']):
        return TikTokRegionBlockedError(f"Region blocked{' in ' + context if context else ''}: {error}")
    
    else:
        return TikTokError(f"TikTok error{' in ' + context if context else ''}: {error}")


def create_retry_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """
    Calculate exponential backoff delay for retries
    
    Args:
        attempt: Attempt number (starting from 0)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        
    Returns:
        Delay in seconds
    """
    delay = base_delay * (2 ** attempt)
    return min(delay, max_delay)


def validate_tiktok_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate TikTok configuration parameters
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check ms_token
    ms_token = config.get('TIKTOK_MS_TOKEN', '')
    if not ms_token:
        errors.append("TIKTOK_MS_TOKEN is not configured (optional but recommended)")
    
    # Check browser
    browser = config.get('TIKTOK_BROWSER', 'chromium')
    valid_browsers = ['chromium', 'firefox', 'webkit']
    if browser not in valid_browsers:
        errors.append(f"TIKTOK_BROWSER must be one of {valid_browsers}")
    
    # Check numeric values
    max_retries = config.get('TIKTOK_MAX_RETRIES', 3)
    if not isinstance(max_retries, int) or max_retries < 1:
        errors.append("TIKTOK_MAX_RETRIES must be a positive integer")
    
    sleep_after = config.get('TIKTOK_SLEEP_AFTER', 3)
    if not isinstance(sleep_after, int) or sleep_after < 0:
        errors.append("TIKTOK_SLEEP_AFTER must be a non-negative integer")
    
    session_count = config.get('TIKTOK_SESSION_COUNT', 1)
    if not isinstance(session_count, int) or session_count < 1:
        errors.append("TIKTOK_SESSION_COUNT must be a positive integer")
    
    return errors


def log_tiktok_metrics(operation: str, **metrics):
    """
    Log TikTok operation metrics
    
    Args:
        operation: Operation name
        **metrics: Metric key-value pairs
    """
    logger.info(f"TikTok {operation} metrics", operation=operation, **metrics)


class TikTokRateLimiter:
    """Simple rate limiter for TikTok API calls"""
    
    def __init__(self, calls_per_minute: int = 30):
        self.calls_per_minute = calls_per_minute
        self.calls = []
    
    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        import asyncio
        
        now = time.time()
        
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls if now - call_time < 60]
        
        # Check if we need to wait
        if len(self.calls) >= self.calls_per_minute:
            oldest_call = min(self.calls)
            wait_time = 60 - (now - oldest_call)
            if wait_time > 0:
                logger.info(f"Rate limiting: waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
        
        # Record this call
        self.calls.append(now)