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

logger = configure_logging("video-crawler")

class YoutubeSearcher:
    def __init__(self, platform_name: str):
        self.platform_name = platform_name

    async def search_youtube(self, query: str, recency_days: int, num_ytb_videos: int = 10) -> List[Dict[str, Any]]:
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
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': 'discard_in_playlist',
                'playlistend': current_search_limit,
            }
            
            search_query = f"ytsearch{current_search_limit}:{query}"
            
            logger.info(f"Attempt {attempts}/{MAX_ATTEMPTS}: Searching YouTube for query: '{query}' with recency_days: {recency_days}, num_ytb_videos: {num_ytb_videos} (current search limit: {current_search_limit})")
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(search_query, download=False)
                    entries = info.get('entries', [])
                    
                    logger.info(f"Retrieved {len(entries)} raw search results for query: '{query}' in attempt {attempts}")
                    logger.debug(f"Entries: {entries}")

                    videos = []
                    cutoff_date = datetime.utcnow() - timedelta(days=recency_days)
                    
                    # Create and configure filter chain
                    filter_chain = FilterChain()
                    filter_chain.add_filter("valid_entry", filter_valid_entry)
                    filter_chain.add_filter("duration", filter_duration)
                    
                    # Apply filters to entries
                    filtered_entries, skipped_count = filter_chain.apply(entries, cutoff_date)
                    
                    # Convert filtered entries to video metadata
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
                    
                    # Take up to num_ytb_videos from the filtered results
                    final_videos = videos[:num_ytb_videos]
                    
                    logger.info(f"Found {len(final_videos)} videos for query '{query}' after filtering in attempt {attempts} (skipped {skipped_count} entries)")
                    
                    if len(final_videos) < num_ytb_videos:
                        current_search_limit += num_ytb_videos # Increase search limit for next attempt
                        logger.info(f"Not enough videos found. Increasing search limit to {current_search_limit} for next attempt.")
                    
            except Exception as e:
                logger.error(f"Failed to search YouTube for '{query}' in attempt {attempts}: {str(e)}")
                # If an error occurs, we should break the loop to avoid infinite retries on persistent errors
                break
        
        return final_videos
