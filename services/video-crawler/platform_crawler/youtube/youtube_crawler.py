import asyncio
import random
from typing import Any, Dict, List

from common_py.logging_config import configure_logging
from config_loader import config
from platform_crawler.common.base_crawler import BaseVideoCrawler
from platform_crawler.youtube.downloader import YoutubeDownloader
from platform_crawler.youtube.youtube_searcher import YoutubeSearcher
from platform_crawler.youtube.youtube_utils import is_url_like

logger = configure_logging("video-crawler:youtube_crawler")


class YoutubeCrawler(BaseVideoCrawler):
    """YouTube video crawler using yt-dlp for search and download"""

    def __init__(self):
        super().__init__(platform_name="youtube", logger=logger)
        self.searcher = YoutubeSearcher(self.platform_name)
        self.downloader = YoutubeDownloader()
        self._dedupe_key = "video_id"

    def _prepare_queries(
        self, queries: List[str], recency_days: int, num_videos: int
    ) -> List[str]:
        normalized_queries = super()._prepare_queries(queries, recency_days, num_videos)
        filtered_queries = [query for query in normalized_queries if not is_url_like(query)]
        skipped = len(normalized_queries) - len(filtered_queries)
        if skipped:
            self.logger.info(
                "Skipping %s URL-like queries out of %s",
                skipped,
                len(normalized_queries),
            )
        if not filtered_queries:
            self.logger.info(
                "No keyword queries available after filtering URL-like inputs; skipping search"
            )
        return filtered_queries

    async def _search_videos_for_queries(
        self, queries: List[str], recency_days: int, num_videos: int
    ) -> List[Dict[str, Any]]:
        all_videos: List[Dict[str, Any]] = []
        for index, query in enumerate(queries):
            try:
                self.logger.info("Searching YouTube for: %s", query)
                search_results = await self.searcher.search_youtube(
                    query,
                    recency_days,
                    num_videos,
                )
                self.logger.info(
                    "Found %s videos for query '%s'",
                    len(search_results),
                    query,
                )
                all_videos.extend(search_results)

                if index < len(queries) - 1:
                    delay = random.uniform(1.0, 3.0)
                    self.logger.info(
                        "Waiting %.1fs before next query to avoid rate limiting",
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
        videos_list = list(videos.values())
        if not videos_list:
            return []

        semaphore = asyncio.Semaphore(config.NUM_PARALLEL_DOWNLOADS)
        active_downloads = 0
        max_concurrent = 0

        async def download_single_video(video: Dict[str, Any]):
            nonlocal active_downloads, max_concurrent

            active_downloads += 1
            max_concurrent = max(max_concurrent, active_downloads)
            self.logger.info(
                "[CONCURRENCY] Active downloads: %s | Max so far: %s | Starting: %s",
                active_downloads,
                max_concurrent,
                video.get("title"),
            )

            async with semaphore:
                try:
                    downloaded_video = await self.downloader.download_video(video, download_dir)
                    return downloaded_video
                except Exception as exc:
                    self.logger.error(
                        "[CONCURRENCY] Active downloads: %s | Exception: %s | Error: %s",
                        active_downloads,
                        video.get("title"),
                        str(exc),
                    )
                    self.logger.error(
                        "Full traceback for video '%s':",
                        video.get("title"),
                        exc_info=True,
                    )
                    return None
                finally:
                    active_downloads -= 1
                    self.logger.info(
                        "[CONCURRENCY] Active downloads: %s | Finished: %s",
                        active_downloads,
                        video.get("title"),
                    )

        self.logger.info(
            "[PARALLEL-START] Starting %s video downloads with %s concurrent limit",
            len(videos_list),
            config.NUM_PARALLEL_DOWNLOADS,
        )
        start_time = asyncio.get_event_loop().time()

        tasks = [download_single_video(video) for video in videos_list]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        downloaded_videos = [result for result in results if result is not None]

        total_time = asyncio.get_event_loop().time() - start_time
        avg_time = total_time / len(videos_list) if videos_list else 0
        self.logger.info(
            "[PARALLEL-FINISH] Completed %s/%s downloads | Max concurrent: %s | Total time: %.2fs | Average per download: %.2fs",
            len(downloaded_videos),
            len(videos_list),
            max_concurrent,
            total_time,
            avg_time,
        )

        return downloaded_videos

    async def _download_unique_videos(
        self, unique_videos: Dict[Any, Dict[str, Any]], download_dir: str
    ) -> List[Dict[str, Any]]:
        """Backward-compatible wrapper for existing tests."""
        return await self._download_videos(unique_videos, download_dir)
