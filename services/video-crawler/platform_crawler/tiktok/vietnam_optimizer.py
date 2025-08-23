"""
Vietnam-specific optimizations and proxy support for TikTok
"""
import asyncio
import random
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from common_py.logging_config import configure_logging
from .tiktok_utils import TikTokRateLimiter

logger = configure_logging("tiktok-vietnam")


class VietnamTikTokOptimizer:
    """
    Vietnam-specific optimizations for TikTok API access
    """
    
    def __init__(self):
        self.rate_limiter = TikTokRateLimiter(calls_per_minute=20)  # More conservative for Vietnam
        self.vietnam_proxies = []
        self.current_proxy_index = 0
    
    def add_vietnam_proxy(self, proxy_url: str):
        """
        Add a Vietnam-based proxy server
        
        Args:
            proxy_url: Proxy URL in format http://user:pass@host:port
        """
        try:
            parsed = urlparse(proxy_url)
            if parsed.scheme and parsed.netloc:
                self.vietnam_proxies.append(proxy_url)
                logger.info("Added Vietnam proxy", proxy_host=parsed.netloc)
            else:
                logger.error("Invalid proxy URL format", proxy_url=proxy_url)
        except Exception as e:
            logger.error("Error adding Vietnam proxy", proxy_url=proxy_url, error=str(e))
    
    def get_next_vietnam_proxy(self) -> Optional[str]:
        """
        Get the next Vietnam proxy in rotation
        
        Returns:
            Proxy URL or None if no proxies available
        """
        if not self.vietnam_proxies:
            return None
        
        proxy = self.vietnam_proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.vietnam_proxies)
        
        return proxy
    
    async def wait_for_rate_limit(self):
        """Wait if needed to respect Vietnam-specific rate limits"""
        await self.rate_limiter.wait_if_needed()
    
    def enhance_search_queries_for_vietnam(self, queries: List[str]) -> List[str]:
        """
        Enhance search queries with Vietnam-specific terms
        
        Args:
            queries: Original search queries
            
        Returns:
            Enhanced queries with Vietnamese context
        """
        enhanced_queries = []
        
        vietnam_terms = [
            "vietnam", "việt nam", "vn", "vietnamese",
            "sài gòn", "hà nội", "đà nẵng", "hồ chí minh"
        ]
        
        for query in queries:
            # Add original query
            enhanced_queries.append(query)
            
            # Add query with Vietnam context
            for term in vietnam_terms[:2]:  # Use first 2 terms to avoid too many queries
                enhanced_query = f"{query} {term}"
                if enhanced_query not in enhanced_queries:
                    enhanced_queries.append(enhanced_query)
        
        logger.info("Enhanced queries for Vietnam", 
                   original_count=len(queries),
                   enhanced_count=len(enhanced_queries))
        
        return enhanced_queries
    
    def get_vietnam_hashtags_for_query(self, query: str) -> List[str]:
        """
        Generate Vietnam-relevant hashtags for a query
        
        Args:
            query: Search query
            
        Returns:
            List of Vietnam-relevant hashtags
        """
        vietnam_hashtags = [
            "vietnam", "vietnamtravel", "vietnamfood", "vietnamlife",
            "saigon", "hanoi", "danang", "hochiminh", "vietnamese",
            "madeincietnam", "vietnamculture", "vietnamproduct"
        ]
        
        # Combine query with Vietnam hashtags
        query_hashtags = []
        clean_query = query.lower().replace(" ", "")
        
        for hashtag in vietnam_hashtags:
            combined = f"{clean_query}{hashtag}"
            if len(combined) <= 50:  # TikTok hashtag length limit
                query_hashtags.append(combined)
        
        return query_hashtags[:5]  # Limit to 5 hashtags
    
    def optimize_session_config_for_vietnam(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize TikTok session configuration for Vietnam access
        
        Args:
            base_config: Base session configuration
            
        Returns:
            Optimized configuration for Vietnam
        """
        vietnam_config = base_config.copy()
        
        # Use Vietnam proxy if available
        vietnam_proxy = self.get_next_vietnam_proxy()
        if vietnam_proxy:
            vietnam_config["proxy"] = vietnam_proxy
        
        # More conservative session settings for Vietnam
        vietnam_config["sleep_after"] = max(vietnam_config.get("sleep_after", 3), 5)
        vietnam_config["headless"] = True  # Always headless for better performance
        
        # Add Vietnam-specific user agent
        vietnam_config["user_agent"] = self._get_vietnam_user_agent()
        
        logger.info("Optimized session config for Vietnam", has_proxy=bool(vietnam_proxy))
        
        return vietnam_config
    
    def _get_vietnam_user_agent(self) -> str:
        """Get a user agent string appropriate for Vietnam"""
        vietnam_user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ]
        
        return random.choice(vietnam_user_agents)
    
    async def validate_vietnam_access(self, api_client) -> bool:
        """
        Validate that TikTok API can access Vietnam content
        
        Args:
            api_client: TikTok API client instance
            
        Returns:
            True if Vietnam access is working
        """
        try:
            # Try searching for a common Vietnamese term
            test_videos = await api_client.search_videos("vietnam", count=1)
            
            if test_videos and len(test_videos) > 0:
                logger.info("Vietnam TikTok access validated successfully")
                return True
            else:
                logger.warning("Vietnam TikTok access validation failed - no results")
                return False
                
        except Exception as e:
            logger.error("Vietnam TikTok access validation error", error=str(e))
            return False
    
    def get_vietnam_peak_hours(self) -> List[int]:
        """
        Get peak usage hours in Vietnam (UTC+7)
        
        Returns:
            List of peak hours (0-23) in UTC
        """
        # Vietnam peak hours: 7-9 PM local time (12-14 UTC)
        # and 12-2 PM local time (5-7 UTC)
        return [5, 6, 7, 12, 13, 14]
    
    def is_vietnam_peak_hour(self) -> bool:
        """
        Check if current time is peak hour in Vietnam
        
        Returns:
            True if currently peak hour in Vietnam
        """
        import datetime
        
        utc_hour = datetime.datetime.utcnow().hour
        peak_hours = self.get_vietnam_peak_hours()
        
        return utc_hour in peak_hours
    
    async def apply_vietnam_throttling(self):
        """Apply additional throttling during Vietnam peak hours"""
        if self.is_vietnam_peak_hour():
            # Additional delay during peak hours
            delay = random.uniform(2, 5)
            logger.info(f"Applying Vietnam peak hour throttling: {delay:.1f}s")
            await asyncio.sleep(delay)


class VietnamContentFilter:
    """
    Filter and enhance content specifically for Vietnam market
    """
    
    def __init__(self):
        self.vietnamese_keywords = [
            "việt", "vietnam", "vietnamese", "vn", "sài gòn", "hà nội",
            "đà nẵng", "hồ chí minh", "mekong", "phở", "bánh", "cơm",
            "tiếng việt", "văn hóa", "truyền thống"
        ]
        
        self.vietnam_product_categories = [
            "điện tử", "thời trang", "mỹ phẩm", "gia dụng", "thực phẩm",
            "đồ chơi", "sách", "điện thoại", "laptop", "máy tính"
        ]
    
    def is_vietnam_relevant(self, video: Dict[str, Any]) -> bool:
        """
        Check if video content is relevant to Vietnam market
        
        Args:
            video: Video metadata dictionary
            
        Returns:
            True if relevant to Vietnam
        """
        title = video.get("title", "").lower()
        author = video.get("author", "").lower()
        
        # Check for Vietnamese keywords in title or author
        for keyword in self.vietnamese_keywords:
            if keyword in title or keyword in author:
                return True
        
        # Check for Vietnam product categories
        for category in self.vietnam_product_categories:
            if category in title:
                return True
        
        return False
    
    def score_vietnam_relevance(self, video: Dict[str, Any]) -> float:
        """
        Score how relevant a video is to Vietnam market (0.0 to 1.0)
        
        Args:
            video: Video metadata dictionary
            
        Returns:
            Relevance score (higher = more relevant)
        """
        score = 0.0
        title = video.get("title", "").lower()
        author = video.get("author", "").lower()
        
        # Score based on Vietnamese keywords
        for keyword in self.vietnamese_keywords:
            if keyword in title:
                score += 0.3
            if keyword in author:
                score += 0.2
        
        # Score based on product categories
        for category in self.vietnam_product_categories:
            if category in title:
                score += 0.1
        
        # Score based on engagement (assuming Vietnam audience)
        view_count = video.get("view_count", 0)
        if view_count > 10000:
            score += 0.1
        if view_count > 100000:
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def filter_for_vietnam_market(self, videos: List[Dict[str, Any]], 
                                 min_score: float = 0.3) -> List[Dict[str, Any]]:
        """
        Filter videos for Vietnam market relevance
        
        Args:
            videos: List of video metadata
            min_score: Minimum relevance score required
            
        Returns:
            Filtered list of Vietnam-relevant videos
        """
        vietnam_videos = []
        
        for video in videos:
            score = self.score_vietnam_relevance(video)
            if score >= min_score:
                video["vietnam_relevance_score"] = score
                vietnam_videos.append(video)
        
        # Sort by relevance score (highest first)
        vietnam_videos.sort(key=lambda v: v["vietnam_relevance_score"], reverse=True)
        
        logger.info("Filtered videos for Vietnam market", 
                   original_count=len(videos),
                   filtered_count=len(vietnam_videos),
                   min_score=min_score)
        
        return vietnam_videos
    
    def enhance_video_metadata_for_vietnam(self, video: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance video metadata with Vietnam-specific information
        
        Args:
            video: Original video metadata
            
        Returns:
            Enhanced video metadata
        """
        enhanced = video.copy()
        
        # Add Vietnam relevance score
        enhanced["vietnam_relevance_score"] = self.score_vietnam_relevance(video)
        
        # Add Vietnam market category
        enhanced["vietnam_market_category"] = self._categorize_for_vietnam_market(video)
        
        # Add Vietnamese language detection
        enhanced["has_vietnamese_content"] = self._has_vietnamese_content(video)
        
        return enhanced
    
    def _categorize_for_vietnam_market(self, video: Dict[str, Any]) -> str:
        """Categorize video for Vietnam market"""
        title = video.get("title", "").lower()
        
        category_keywords = {
            "technology": ["điện thoại", "laptop", "máy tính", "công nghệ"],
            "fashion": ["thời trang", "quần áo", "giày", "túi xách"],
            "food": ["đồ ăn", "món ăn", "phở", "bánh", "cơm"],
            "beauty": ["mỹ phẩm", "làm đẹp", "skincare", "makeup"],
            "lifestyle": ["cuộc sống", "văn hóa", "du lịch", "giải trí"]
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in title for keyword in keywords):
                return category
        
        return "general"
    
    def _has_vietnamese_content(self, video: Dict[str, Any]) -> bool:
        """Check if video contains Vietnamese content"""
        title = video.get("title", "")
        
        # Simple Vietnamese character detection
        vietnamese_chars = "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
        
        return any(char in title.lower() for char in vietnamese_chars)