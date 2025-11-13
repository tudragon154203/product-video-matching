"""TikTok video crawler implementation."""

import asyncio
from typing import Any, Dict, Iterable, List

from common_py.logging_config import configure_logging
from config_loader import config
from platform_crawler.common.base_crawler import BaseVideoCrawler
from platform_crawler.common.utils import deduplicate_by_key, deduplicate_videos_by_id_and_title
from platform_crawler.tiktok.tiktok_downloader import TikTokDownloader
from platform_crawler.tiktok.tiktok_searcher import TikTokSearcher

logger = configure_logging("video-crawler:tiktok_crawler")


class TikTokCrawler(BaseVideoCrawler):
    """TikTok video crawler implementation."""

    def __init__(self):
        super().__init__(platform_name="tiktok", logger=logger, enable_title_deduplication=True)
        self.searcher = TikTokSearcher(self.platform_name)
        self.downloader_config = {
            "TIKTOK_VIDEO_STORAGE_PATH": config.TIKTOK_VIDEO_STORAGE_PATH,
            "TIKTOK_KEYFRAME_STORAGE_PATH": config.TIKTOK_KEYFRAME_STORAGE_PATH,
            "TIKTOK_CRAWL_HOST": config.TIKTOK_CRAWL_HOST,
            "TIKTOK_CRAWL_HOST_PORT": config.TIKTOK_CRAWL_HOST_PORT,
            "TIKTOK_DOWNLOAD_STRATEGY": config.TIKTOK_DOWNLOAD_STRATEGY,
            "TIKTOK_DOWNLOAD_TIMEOUT": config.TIKTOK_DOWNLOAD_TIMEOUT,
            "retries": 3,
            "timeout": 30,
            "platform_name": self.platform_name,
        }
        self.max_parallel_downloads = (
            config.NUM_PARALLEL_DOWNLOADS
            if config.NUM_PARALLEL_DOWNLOADS and config.NUM_PARALLEL_DOWNLOADS > 0
            else 1
        )
        self.downloader = TikTokDownloader(self.downloader_config)
        self._dedupe_key = "id"

    async def _search_videos_for_queries(
        self, queries: List[str], recency_days: int, num_videos: int
    ) -> List[Dict[str, Any]]:
        all_videos: List[Dict[str, Any]] = []
        for index, query in enumerate(queries):
            try:
                self.logger.info("Searching TikTok for: %s", query)
                search_response = await self.searcher.search_tiktok(query, num_videos)
                self.logger.info(
                    "Found %s videos for query '%s'",
                    len(search_response.results),
                    query,
                )

                for tiktok_video in search_response.results:
                    video_data = {
                        "id": tiktok_video.id,
                        "caption": tiktok_video.caption,
                        "authorHandle": tiktok_video.author_handle,
                        "likeCount": tiktok_video.like_count,
                        "uploadTime": tiktok_video.upload_time,
                        "webViewUrl": tiktok_video.web_view_url,
                    }
                    all_videos.append(video_data)

                if index < len(queries) - 1:
                    delay = 1.0
                    self.logger.info(
                        "Waiting %ss before next query to avoid rate limiting",
                        delay,
                    )
                    await asyncio.sleep(delay)
            except Exception as exc:
                self.logger.error(
                    "Failed to search for query '%s': %s",
                    query,
                    str(exc),
                )
                self.logger.error(
                    "Full traceback for query '%s':",
                    query,
                    exc_info=True,
                )
                continue
        return all_videos

    async def _download_videos(
        self, videos: Dict[Any, Dict[str, Any]], download_dir: str
    ) -> List[Dict[str, Any]]:
        return await self.downloader.download_videos_batch(
            videos,
            download_dir,
            self.max_parallel_downloads,
        )

    def _deduplicate_videos(
        self,
        videos: Iterable[Dict[str, Any]],
    ) -> Dict[Any, Dict[str, Any]]:
        if self._enable_title_deduplication:
            # Use new title-based deduplication with caption mapping for TikTok
            deduped_videos = deduplicate_videos_by_id_and_title(
                videos,
                id_keys=self._dedupe_key,
                title_key="caption"  # TikTok uses "caption" field
            )
            # Convert to dict format for compatibility with existing code
            return {f"video_{i}": video for i, video in enumerate(deduped_videos)}
        else:
            # Use existing ID-only deduplication
            return deduplicate_by_key(videos, self._dedupe_key)
