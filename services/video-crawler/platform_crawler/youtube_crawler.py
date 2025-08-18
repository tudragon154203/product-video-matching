import os
import re
import asyncio
from typing import List, Dict, Any, Callable, Protocol
from pathlib import Path
from datetime import datetime, timedelta
import yt_dlp
from common_py.logging_config import configure_logging
from .interface import PlatformCrawlerInterface
from utils.filter_chain import FilterChain
from utils.youtube_filters import (
    filter_valid_entry,
    filter_upload_date,
    filter_duration
)

logger = configure_logging("video-crawler")


class YoutubeCrawler(PlatformCrawlerInterface):
    """YouTube video crawler using yt-dlp for search and download"""
    
    def __init__(self):
        self.platform_name = "youtube"
    
    def _is_url_like(self, query: str) -> bool:
        """Check if query looks like a URL (should be skipped)"""
        url_patterns = [
            r'^https?://',
            r'^www\.',
            r'^youtube\.com/',
            r'^youtu\.be/',
            r'^[a-zA-Z0-9_-]{11}$'  # YouTube video ID pattern
        ]
        # Check if any pattern matches the query
        for pattern in url_patterns:
            if re.match(pattern, query):
                return True
        return False
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file system usage"""
        # Replace spaces with underscores first
        filename = filename.replace(' ', '_')
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove leading/trailing whitespace and dots
        filename = filename.strip('. ')
        # Limit length to prevent issues
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    async def search_and_download_videos(
        self, queries: List[str], recency_days: int, download_dir: str, num_ytb_videos: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for videos on YouTube and download them
        
        Args:
            queries: List of search queries (keywords only)
            recency_days: How many days back to search for videos
            download_dir: Directory path where videos should be saved (should be {VIDEO_DIR}/youtube)
            num_ytb_videos: Number of YouTube videos to search for per query
                (actual downloaded videos may be fewer due to filtering)
            
        Returns:
            List of video metadata dictionaries with required fields
        """
        logger.info(f"Starting search_and_download_videos with {len(queries)} queries, recency_days={recency_days}, num_ytb_videos={num_ytb_videos}")
        
        # Ensure download directory exists
        Path(download_dir).mkdir(parents=True, exist_ok=True)
        
        all_videos = []
        
        for query in queries:
            try:
                # Skip URL-like inputs
                if self._is_url_like(query):
                    logger.info(f"Skipping URL-like query: {query}")
                    continue
                
                logger.info(f"Searching YouTube for: {query}")
                
                # Search for videos using yt-dlp
                search_results = await self._search_youtube(query, recency_days, num_ytb_videos)
                
                logger.info(f"Found {len(search_results)} videos for query '{query}'")
                
                # Add to our results
                all_videos.extend(search_results)
                
            except Exception as e:
                logger.error(f"Failed to search for query '{query}': {str(e)}")
                continue
        
        logger.info(f"Total videos found across all queries: {len(all_videos)}")
        
        # Deduplicate by video_id
        unique_videos = {}
        for video in all_videos:
            video_id = video['video_id']
            if video_id not in unique_videos:
                unique_videos[video_id] = video
        
        logger.info(f"Unique videos after deduplication: {len(unique_videos)}")
        
        # Download videos
        downloaded_videos = []
        for video in unique_videos.values():
            try:
                logger.info(f"Attempting to download video: {video['title']} ({video['video_id']})")
                downloaded_video = await self._download_video(video, download_dir)
                if downloaded_video:
                    downloaded_videos.append(downloaded_video)
                    logger.info(f"Successfully downloaded video: {video['title']} ({video['video_id']})")
                else:
                    logger.warning(f"Failed to download video: {video['title']} ({video['video_id']})")
            except Exception as e:
                logger.error(f"Failed to download video {video['video_id']}: {str(e)}")
                continue
        
        logger.info(f"Successfully downloaded {len(downloaded_videos)} videos out of {len(unique_videos)} unique videos")
        return downloaded_videos
    
    async def _search_youtube(self, query: str, recency_days: int, num_ytb_videos: int = 10) -> List[Dict[str, Any]]:
        """
        Search YouTube for videos matching the query and recency filter
        
        Args:
            query: Search query
            recency_days: How many days back to search
            num_ytb_videos: Number of YouTube videos to search for
            
        Returns:
            List of video metadata dictionaries
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'discard_in_playlist',
            'playlistend': num_ytb_videos,  # Limit search results
        }
        
        search_query = f"ytsearch{num_ytb_videos}:{query}"
        
        logger.info(f"Starting YouTube search for query: '{query}' with recency_days: {recency_days}, num_ytb_videos: {num_ytb_videos}")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                
                total_entries = len(info.get('entries', []))
                logger.info(f"Retrieved {total_entries} raw search results for query: '{query}'")
                
                videos = []
                cutoff_date = datetime.utcnow() - timedelta(days=recency_days)
                
                # Create and configure filter chain
                filter_chain = FilterChain()
                filter_chain.add_filter(filter_valid_entry)
                filter_chain.add_filter(filter_upload_date)
                filter_chain.add_filter(filter_duration)
                
                # Apply filters to entries
                filtered_entries, skipped_count = filter_chain.apply(info.get('entries', []), cutoff_date)
                
                # Convert filtered entries to video metadata
                for entry in filtered_entries:
                    # Parse upload date (we know it's valid because filters passed)
                    upload_date_str = entry.get('upload_date')
                    upload_date = datetime.strptime(upload_date_str, '%Y%m%d')
                    upload_date = upload_date.replace(tzinfo=None)
                    
                    video = {
                        'platform': self.platform_name,
                        'video_id': entry['id'],
                        'url': f"https://www.youtube.com/watch?v={entry['id']}",
                        'title': entry.get('title', ''),
                        'duration_s': entry['duration'],
                        'published_at': upload_date.strftime('%Y-%m-%d'),
                        'uploader': entry.get('uploader', 'unknown'),
                    }
                    
                    videos.append(video)
                
                logger.info(f"Found {len(videos)} videos for query '{query}' (skipped {skipped_count} entries)")
                logger.debug(f"Video details: {[{'id': v['video_id'], 'title': v['title'], 'date': v['published_at']} for v in videos]}")
                return videos
                
        except Exception as e:
            logger.error(f"Failed to search YouTube for '{query}': {str(e)}")
            return []
    
    async def _download_video(self, video: Dict[str, Any], download_dir: str) -> Dict[str, Any]:
        """
        Download a single video to the specified directory
        
        Args:
            video: Video metadata dictionary
            download_dir: Base download directory
            
        Returns:
            Video metadata with local_path added, or None if download failed
        """
        video_id = video['video_id']
        uploader = self._sanitize_filename(video['uploader'])
        title = self._sanitize_filename(video['title'])
        
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
        
        # Download the video
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': str(uploader_dir / f"{title}.%(ext)s"),
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
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
            return None