import re
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta
import yt_dlp
from common_py.logging_config import configure_logging
from utils.filter_chain import FilterChain
from utils.youtube_filters import (
    filter_valid_entry,
    filter_duration
)
from config_loader import config # Import config

logger = configure_logging("video-crawler", log_level=config.LOG_LEVEL)

class YoutubeSearcher:
    def __init__(self, platform_name: str):
        self.platform_name = platform_name

    async def search_youtube(self, query: str, recency_days: int, num_ytb_videos: int) -> List[Dict[str, Any]]:
        """
        Search YouTube for videos matching the query and recency filter
        
        Args:
            query: Search query
            recency_days: How many days back to search
            num_ytb_videos: Number of YouTube videos to search for
            
        Returns:
            List of video metadata dictionaries
        """
        MAX_ATTEMPTS = 5
        current_search_limit = num_ytb_videos
        attempts = 0
        final_videos = []

        while len(final_videos) < num_ytb_videos and attempts < MAX_ATTEMPTS:
            attempts += 1
            logger.info(f"Attempt {attempts}/{MAX_ATTEMPTS}: Searching YouTube for query: '{query}' with recency_days: {recency_days}, num_ytb_videos: {num_ytb_videos} (current search limit: {current_search_limit})")
            
            try:
                entries = await self._perform_yt_dlp_search(query, current_search_limit)
                logger.info(f"Retrieved {len(entries)} raw search results for query: '{query}' in attempt {attempts}")
                logger.debug(f"Entries: {entries}")

                videos = self._filter_and_format_entries(entries, recency_days)
                
                final_videos = videos[:num_ytb_videos]
                
                logger.info(f"Found {len(final_videos)} videos for query '{query}' after filtering in attempt {attempts}")
                
                if len(final_videos) < num_ytb_videos:
                    current_search_limit += num_ytb_videos # Increase search limit for next attempt
                    logger.info(f"Not enough videos found. Increasing search limit to {current_search_limit} for next attempt.")
                    
            except Exception as e:
                logger.error(f"Failed to search YouTube for '{query}' in attempt {attempts}: {str(e)}")
                break
        
        return final_videos

    async def _perform_yt_dlp_search(self, query: str, search_limit: int) -> List[Dict[str, Any]]:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'discard_in_playlist',
            'playlistend': search_limit,
        }
        search_query = f"ytsearch{search_limit}:{query}"
        logger.debug(f"Performing yt-dlp search with query: '{search_query}' and options: {ydl_opts}")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                return info.get('entries', [])
        except Exception as e:
            logger.error(f"yt-dlp search failed for query '{search_query}': {e}", exc_info=True)
            raise # Re-raise the exception to be caught by the outer try-except block

    def _filter_and_format_entries(self, entries: List[Dict[str, Any]], recency_days: int) -> List[Dict[str, Any]]:
        videos = []
        cutoff_date = datetime.utcnow() - timedelta(days=recency_days)
        
        filter_chain = FilterChain()
        filter_chain.add_filter("valid_entry", filter_valid_entry)
        filter_chain.add_filter("duration", filter_duration)
        
        filtered_entries, skipped_count = filter_chain.apply(entries, cutoff_date)
        
        for entry in filtered_entries:
            video = {
                'platform': self.platform_name,
                'video_id': entry['id'],
                'url': f"https://www.youtube.com/watch?v={entry['id']}",
                'title': entry.get('title', ''),
                'duration_s': entry['duration'],
                'uploader': entry.get('uploader', 'unknown'),
            }
            videos.append(video)
        
        return videos
