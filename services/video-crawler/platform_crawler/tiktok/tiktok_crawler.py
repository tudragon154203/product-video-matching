"""TikTok video crawler implementation."""

import asyncio
from pathlib import Path
from typing import Any, Dict, List

from common_py.logging_config import configure_logging
from platform_crawler.interface import PlatformCrawlerInterface
from platform_crawler.tiktok.tiktok_searcher import TikTokSearcher

logger = configure_logging("video-crawler:tiktok_crawler")


class TikTokCrawler(PlatformCrawlerInterface):
    """TikTok video crawler implementation."""

    def __init__(self):
        self.platform_name = "tiktok"
        self.searcher = TikTokSearcher(self.platform_name)

    async def search_and_download_videos(
        self, queries: List[str], recency_days: int, download_dir: str, num_videos: int
    ) -> List[Dict[str, Any]]:
        """
        Search for videos on TikTok and return metadata.

        Args:
            queries: List of search queries
            recency_days: How many days back to search for videos (not used by TikTok API)
            download_dir: Directory path where videos should be saved
            num_videos: Number of TikTok videos to search for per query

        Returns:
            List of video metadata dictionaries
        """
        logger.info(
            f"Starting search_and_download_videos with {len(queries)} queries, recency_days={recency_days}, num_videos={num_videos}")

        Path(download_dir).mkdir(parents=True, exist_ok=True)

        all_videos = await self._search_videos_for_queries(queries, num_videos)
        logger.info(f"Total videos found across all queries: {len(all_videos)}")

        unique_videos = self._deduplicate_videos(all_videos)
        logger.info(f"Unique videos after deduplication: {len(unique_videos)}")

        # Convert to the expected format (no actual download for TikTok as videos are not downloaded directly)
        result_videos = []
        for video in unique_videos.values():
            result_video = {
                'platform': self.platform_name,
                'url': video['webViewUrl'],  # Use web view URL as the video URL
                'title': video['caption'],   # Use caption as title
                'video_id': video['id'],     # Use TikTok ID
                'author_handle': video['authorHandle'],
                'like_count': video['likeCount'],
                'upload_time': video['uploadTime'],
                'local_path': None,  # TikTok videos are not downloaded directly in this implementation
                'duration_s': None   # TikTok API doesn't provide duration in search results
            }
            result_videos.append(result_video)

        logger.info(f"Returning {len(result_videos)} videos for platform {self.platform_name}")
        return result_videos

    async def _search_videos_for_queries(self, queries: List[str], num_videos: int) -> List[Dict[str, Any]]:
        all_videos = []
        for i, query in enumerate(queries):
            try:
                logger.info(f"Searching TikTok for: {query}")
                search_response = await self.searcher.search_tiktok(query, num_videos)
                logger.info(f"Found {len(search_response.results)} videos for query '{query}'")

                # Convert TikTokVideo objects to dictionaries
                for tiktok_video in search_response.results:
                    video_data = {
                        'id': tiktok_video.id,
                        'caption': tiktok_video.caption,
                        'authorHandle': tiktok_video.author_handle,
                        'likeCount': tiktok_video.like_count,
                        'uploadTime': tiktok_video.upload_time,
                        'webViewUrl': tiktok_video.web_view_url
                    }
                    all_videos.append(video_data)

                # Add a small delay between queries to avoid rate limiting
                if i < len(queries) - 1:  # Don't delay after the last query
                    delay = 1.0  # 1 second delay between queries
                    logger.info(f"Waiting {delay}s before next query to avoid rate limiting")
                    await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Failed to search for query '{query}': {str(e)}")
                # Log the full traceback for debugging
                logger.error(f"Full traceback for query '{query}':", exc_info=True)
                continue
        return all_videos

    def _deduplicate_videos(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        unique_videos = {}
        for video in videos:
            video_id = video['id']
            if video_id not in unique_videos:
                unique_videos[video_id] = video
        return unique_videos

    async def close(self):
        """Close resources used by the crawler."""
        await self.searcher.close()
