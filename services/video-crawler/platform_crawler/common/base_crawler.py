from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Iterable, List

from platform_crawler.interface import PlatformCrawlerInterface
from .utils import deduplicate_by_key


class BaseVideoCrawler(PlatformCrawlerInterface, ABC):
    """Shared implementation for platform crawlers."""

    def __init__(self, platform_name: str, logger) -> None:
        self.platform_name = platform_name
        self.logger = logger
        self._dedupe_key: str | callable = "video_id"

    async def search_and_download_videos(
        self,
        queries: List[str],
        recency_days: int,
        download_dir: str,
        num_videos: int,
    ) -> List[Dict[str, Any]]:
        prepared_queries = self._prepare_queries(queries, recency_days, num_videos)
        if not prepared_queries:
            self.logger.info(
                "No queries to process for platform %s",
                self.platform_name,
            )
            return []

        Path(download_dir).mkdir(parents=True, exist_ok=True)

        all_videos = await self._search_videos_for_queries(
            prepared_queries,
            recency_days,
            num_videos,
        )
        self.logger.info(
            "Total videos found across all queries: %s",
            len(all_videos),
        )
        if not all_videos:
            return []

        unique_videos = self._deduplicate_videos(all_videos)
        self.logger.info(
            "Unique videos after deduplication: %s",
            len(unique_videos),
        )
        if not unique_videos:
            return []

        downloaded_videos = await self._download_unique_videos(unique_videos, download_dir)
        self.logger.info(
            "Returning %s downloaded videos for platform %s",
            len(downloaded_videos),
            self.platform_name,
        )
        return downloaded_videos

    def _prepare_queries(
        self,
        queries: Iterable[str] | str,
        recency_days: int,
        num_videos: int,
    ) -> List[str]:
        return [query for query in self._normalize_queries(queries) if query]

    def _normalize_queries(self, queries: Iterable[str] | str) -> List[str]:
        if isinstance(queries, str):
            return [queries]
        if isinstance(queries, (list, tuple, set)):
            return [query for query in queries if query]
        return list(queries) if queries else []

    def _deduplicate_videos(
        self,
        videos: Iterable[Dict[str, Any]],
    ) -> Dict[Any, Dict[str, Any]]:
        return deduplicate_by_key(videos, self._dedupe_key)

    async def _download_unique_videos(
        self,
        videos: Dict[Any, Dict[str, Any]],
        download_dir: str,
    ) -> List[Dict[str, Any]]:
        """Backward-compatible helper used by older unit tests."""
        return await self._download_videos(videos, download_dir)

    @abstractmethod
    async def _search_videos_for_queries(
        self,
        queries: List[str],
        recency_days: int,
        num_videos: int,
    ) -> List[Dict[str, Any]]:
        """Return candidate videos for the given queries."""

    @abstractmethod
    async def _download_videos(
        self,
        videos: Dict[Any, Dict[str, Any]],
        download_dir: str,
    ) -> List[Dict[str, Any]]:
        """Download the provided videos and return enriched metadata."""
