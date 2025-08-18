import os
import re
import asyncio
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
import yt_dlp
import logging
from .interface import PlatformCrawlerInterface

logger = logging.getLogger(__name__)


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
        self, queries: List[str], recency_days: int, download_dir: str, num_videos: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search for videos on YouTube and download them
        
        Args:
            queries: List of search queries (keywords only)
            recency_days: How many days back to search for videos
            download_dir: Directory path where videos should be saved (should be {VIDEO_DIR}/youtube)
            
        Returns:
            List of video metadata dictionaries with required fields
        """
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
                search_results = await self._search_youtube(query, recency_days, num_videos)
                
                # Add to our results
                all_videos.extend(search_results)
                
            except Exception as e:
                logger.error(f"Failed to search for query '{query}': {str(e)}")
                continue
        
        # Deduplicate by video_id
        unique_videos = {}
        for video in all_videos:
            video_id = video['video_id']
            if video_id not in unique_videos:
                unique_videos[video_id] = video
        
        # Download videos
        downloaded_videos = []
        for video in unique_videos.values():
            try:
                downloaded_video = await self._download_video(video, download_dir)
                if downloaded_video:
                    downloaded_videos.append(downloaded_video)
            except Exception as e:
                logger.error(f"Failed to download video {video['video_id']}: {str(e)}")
                continue
        
        logger.info(f"Successfully downloaded {len(downloaded_videos)} videos")
        return downloaded_videos
    
    async def _search_youtube(self, query: str, recency_days: int, num_videos: int = 3) -> List[Dict[str, Any]]:
        """
        Search YouTube for videos matching the query and recency filter
        
        Args:
            query: Search query
            recency_days: How many days back to search
            num_videos: Maximum number of videos to return
            
        Returns:
            List of video metadata dictionaries
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'discard_in_playlist',
            'playlistend': num_videos,  # Limit search results
        }
        
        search_query = f"ytsearch{num_videos}:{query}"
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                
                videos = []
                cutoff_date = datetime.utcnow() - timedelta(days=recency_days)
                
                for entry in info.get('entries', []):
                    if not entry:
                        continue
                    
                    # Parse upload date
                    upload_date_str = entry.get('upload_date')
                    if not upload_date_str:
                        continue
                    
                    try:
                        upload_date = datetime.strptime(upload_date_str, '%Y%m%d')
                        upload_date = upload_date.replace(tzinfo=None)  # Remove timezone info for comparison
                        
                        # Filter by recency
                        if upload_date < cutoff_date:
                            continue
                            
                    except ValueError:
                        # If we can't parse the date, skip this video
                        continue
                    
                    # Extract duration
                    duration = entry.get('duration')
                    if duration is None:
                        continue
                    
                    video = {
                        'platform': self.platform_name,
                        'video_id': entry['id'],
                        'url': f"https://www.youtube.com/watch?v={entry['id']}",
                        'title': entry.get('title', ''),
                        'duration_s': duration,
                        'published_at': upload_date.strftime('%Y-%m-%d'),
                        'uploader': entry.get('uploader', 'unknown'),
                    }
                    
                    videos.append(video)
                
                logger.info(f"Found {len(videos)} videos for query '{query}'")
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