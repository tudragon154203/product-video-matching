"""
TikTok Search functionality with keyword queries and filtering
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from common_py.logging_config import configure_logging
from .tiktok_api_client import TikTokApiClient
from config_loader import config

logger = configure_logging("tiktok-searcher")


class TikTokSearcher:
    """
    TikTok search engine with keyword-based search and filtering capabilities
    """

    def __init__(self):
        self.api_client = TikTokApiClient()
    
    async def search_videos_by_keywords(
        self, 
        queries: List[str], 
        recency_days: int = 365,
        num_videos: int = 10,
        min_duration: int = 0,
        max_duration: int = 300
    ) -> List[Dict[str, Any]]:
        """
        Search for videos using keyword queries with filtering
        
        Args:
            queries: List of search keywords/phrases
            recency_days: Only return videos from the last N days
            num_videos: Maximum number of videos per query
            min_duration: Minimum video duration in seconds
            max_duration: Maximum video duration in seconds
            
        Returns:
            List of filtered video metadata dictionaries
        """
        all_videos = []
        
        try:
            async with self.api_client as api_client:
                for query in queries:
                    try:
                        logger.info("Searching TikTok with keyword", query=query, num_videos=num_videos)
                        
                        # Search videos using the query
                        videos = await self._search_by_keyword(query, num_videos * 2)  # Get more for filtering
                        
                        # Apply filters
                        filtered_videos = self._apply_filters(
                            videos, recency_days, min_duration, max_duration
                        )
                        
                        # Limit to requested number
                        limited_videos = filtered_videos[:num_videos]
                        
                        logger.info("Filtered TikTok search results", 
                                   query=query, 
                                   found=len(videos), 
                                   filtered=len(limited_videos))
                        
                        all_videos.extend(limited_videos)
                        
                        # Add delay between queries to avoid rate limiting
                        if len(queries) > 1:
                            await asyncio.sleep(config.TIKTOK_SLEEP_AFTER)
                            
                    except Exception as e:
                        logger.error("Failed to search TikTok with keyword", query=query, error=str(e))
                        continue
        
        except Exception as e:
            logger.error("Failed to initialize TikTok API client", error=str(e))
            return []
        
        # Remove duplicates based on video_id
        unique_videos = self._remove_duplicates(all_videos)
        
        logger.info("Completed TikTok keyword search", 
                   total_queries=len(queries),
                   total_videos=len(unique_videos))
        
        return unique_videos
    
    async def _search_by_keyword(self, keyword: str, count: int) -> List[Dict[str, Any]]:
        """
        Internal method to search by keyword using the API client
        
        Args:
            keyword: Search keyword
            count: Number of videos to search for
            
        Returns:
            List of video metadata dictionaries
        """
        if not self.api_client:
            logger.error("API client not initialized")
            return []
        
        try:
            # Use the API client to search videos
            videos = await self.api_client.search_videos(keyword, count)
            return videos
        except Exception as e:
            logger.error("Failed to search by keyword", keyword=keyword, error=str(e))
            return []
    
    def _apply_filters(
        self, 
        videos: List[Dict[str, Any]], 
        recency_days: int,
        min_duration: int,
        max_duration: int
    ) -> List[Dict[str, Any]]:
        """
        Apply filtering criteria to video list
        
        Args:
            videos: List of video metadata dictionaries
            recency_days: Only include videos from the last N days
            min_duration: Minimum video duration in seconds
            max_duration: Maximum video duration in seconds
            
        Returns:
            Filtered list of video metadata dictionaries
        """
        if not videos:
            return []
        
        filtered_videos = []
        cutoff_time = datetime.now().timestamp() - (recency_days * 24 * 60 * 60)
        
        logger.info("Applying filters to TikTok videos", 
                   total_videos=len(videos),
                   recency_days=recency_days,
                   min_duration=min_duration,
                   max_duration=max_duration,
                   cutoff_timestamp=cutoff_time)
        
        for video in videos:
            try:
                video_id = video.get('video_id', 'unknown')
                
                # Check recency (if create_time is available)
                create_time = video.get('create_time', 0)
                if create_time and create_time < cutoff_time:
                    logger.debug("Video filtered out by recency", 
                               video_id=video_id,
                               create_time=create_time,
                               cutoff_time=cutoff_time)
                    continue
                
                # Check duration
                duration = video.get('duration_s', 0)
                if duration < min_duration or duration > max_duration:
                    logger.debug("Video filtered out by duration", 
                               video_id=video_id,
                               duration=duration,
                               min_duration=min_duration,
                               max_duration=max_duration)
                    continue
                
                # Check that essential fields are present
                if not video.get('video_id') or not video.get('url'):
                    logger.debug("Video filtered out by missing essential fields", 
                               video_id=video_id,
                               has_video_id=bool(video.get('video_id')),
                               has_url=bool(video.get('url')))
                    continue
                
                filtered_videos.append(video)
                logger.debug("Video passed all filters", video_id=video_id)
                
            except Exception as e:
                logger.warning("Error filtering video", video_id=video.get('video_id'), error=str(e))
                continue
        
        logger.info("Filtering completed", 
                   input_videos=len(videos),
                   output_videos=len(filtered_videos),
                   filtered_out=len(videos) - len(filtered_videos))
        
        return filtered_videos
    
    def _remove_duplicates(self, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate videos based on video_id
        
        Args:
            videos: List of video metadata dictionaries
            
        Returns:
            List with duplicate videos removed
        """
        seen_ids = set()
        unique_videos = []
        
        for video in videos:
            video_id = video.get('video_id')
            if video_id and video_id not in seen_ids:
                seen_ids.add(video_id)
                unique_videos.append(video)
        
        return unique_videos
    
    def _is_vietnamese_content(self, video: Dict[str, Any]) -> bool:
        """
        Check if video content is Vietnamese (basic heuristic)
        
        Args:
            video: Video metadata dictionary
            
        Returns:
            True if likely Vietnamese content
        """
        # This is a basic heuristic - can be improved with language detection
        title = video.get('title', '').lower()
        vietnamese_indicators = [
            'việt', 'nam', 'vn', 'sài gòn', 'hà nội', 'hồ chí minh',
            'đà nẵng', 'tiếng việt', 'vietnamese', 'vietnam'
        ]
        
        return any(indicator in title for indicator in vietnamese_indicators)
    
    async def search_vietnamese_content(
        self, 
        queries: List[str], 
        recency_days: int = 365,
        num_videos: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search specifically for Vietnamese TikTok content
        
        Args:
            queries: List of search keywords (preferably in Vietnamese)
            recency_days: Only return videos from the last N days
            num_videos: Maximum number of videos per query
            
        Returns:
            List of Vietnamese video metadata dictionaries
        """
        # Add Vietnamese-specific search terms
        vietnamese_queries = []
        for query in queries:
            vietnamese_queries.append(query)
            vietnamese_queries.append(f"{query} vietnam")
            vietnamese_queries.append(f"{query} việt nam")
        
        # Search with enhanced queries
        all_videos = await self.search_videos_by_keywords(
            vietnamese_queries, recency_days, num_videos
        )
        
        # Filter for Vietnamese content
        vietnamese_videos = [
            video for video in all_videos 
            if self._is_vietnamese_content(video)
        ]
        
        logger.info("Filtered for Vietnamese TikTok content", 
                   total_found=len(all_videos),
                   vietnamese_found=len(vietnamese_videos))
        
        return vietnamese_videos