import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging
from common_py.messaging import MessageBroker
from config_loader import config
from fetcher.video_fetcher import VideoFetcher
from handlers.event_emitter import EventEmitter
from platform_crawler.interface import PlatformCrawlerInterface
from platform_crawler.mock_crawler import MockPlatformCrawler
from platform_crawler.tiktok.tiktok_crawler import TikTokCrawler
from platform_crawler.youtube.youtube_crawler import YoutubeCrawler
from services.platform_query_processor import PlatformQueryProcessor
from services.video_cleanup_service import VideoCleanupService
from services.video_processor import VideoProcessor
from services.exceptions import (
    VideoCrawlerError,
    VideoProcessingError,
    PlatformCrawlerError,
    CleanupOperationError
)
from vision_common import JobProgressManager

logger = configure_logging("video-crawler:service")


class VideoCrawlerService:
    """Main service class for video crawl with refactored architecture."""

    def __init__(
        self,
        db: DatabaseManager,
        broker: MessageBroker,
        video_dir_override: Optional[str] = None
    ):
        self.db = db
        self.broker = broker
        self._video_dir_override = os.fspath(video_dir_override) if video_dir_override else None

        # Initialize components
        self.platform_crawlers = self._initialize_platform_crawlers()
        self.video_fetcher = VideoFetcher(platform_crawlers=self.platform_crawlers)
        self.event_emitter = EventEmitter(broker) if broker else None
        self.job_progress_manager = JobProgressManager(broker) if broker else None

        # Initialize specialized services
        self.video_processor = VideoProcessor(
            db=db,
            event_emitter=self.event_emitter,
            job_progress_manager=self.job_progress_manager,
            video_dir_override=self._video_dir_override
        )
        self.cleanup_service = VideoCleanupService(video_dir_override=self._video_dir_override)

        self._log_cleanup_status()

    def _log_cleanup_status(self) -> None:
        """Log cleanup configuration status."""
        if config.CLEANUP_OLD_VIDEOS:
            logger.info(
                "Video cleanup enabled with retention period of {} days".format(
                    config.VIDEO_RETENTION_DAYS
                )
            )
        else:
            logger.info("Video cleanup is disabled")

    def initialize_keyframe_extractor(self, keyframe_dir: Optional[str] = None) -> None:
        """
        Initialize the keyframe extractor with a specific directory.

        Args:
            keyframe_dir: Optional keyframe directory path. If None, creates directories using config.
        """
        self.video_processor.initialize_keyframe_extractor(keyframe_dir)

    async def handle_videos_search_request(self, event_data: Dict[str, Any]) -> None:
        """Handle video search request with cross-platform parallelism.

        Args:
            event_data: Event data containing job parameters

        Raises:
            VideoCrawlerError: If video search processing fails
            PlatformCrawlerError: If platform crawler encounters errors
        """
        try:
            job_id = event_data["job_id"]
            industry = event_data["industry"]
            queries = event_data["queries"]
            platforms = event_data["platforms"]
            recency_days = event_data["recency_days"]

            logger.info(
                "Processing video search request",
                job_id=job_id,
                industry=industry,
                platforms=platforms
            )

            # Extract platform-specific queries
            platform_queries = PlatformQueryProcessor.extract_platform_queries(queries, platforms)

            # Prepare download directories
            platform_download_dirs = self._prepare_platform_download_dirs(platforms)

            # Search and download videos
            all_videos = await self._search_platforms_parallel(
                platforms=platforms,
                platform_queries=platform_queries,
                recency_days=recency_days,
                platform_download_dirs=platform_download_dirs,
                job_id=job_id
            )

            if not all_videos:
                await self._handle_zero_videos_case(job_id)
                return

            # Update job progress
            await self._update_job_progress(job_id, len(all_videos))

            # Process videos and emit events
            await self._process_and_emit_videos(all_videos, job_id)

            logger.info(
                "Completed video search",
                job_id=job_id,
                total_videos=len(all_videos)
            )

        except Exception as e:
            error_msg = f"Failed to process video search request: {str(e)}"
            logger.error(error_msg)
            raise VideoCrawlerError(error_msg, job_id=event_data.get("job_id"))

    def _prepare_platform_download_dirs(self, platforms: List[str]) -> Dict[str, str]:
        """Prepare download directories for each platform.

        Args:
            platforms: List of platform names

        Returns:
            Dictionary mapping platform names to download directories
        """
        base_video_dir = self._get_video_dir()
        platform_download_dirs: Dict[str, str] = {}

        for platform in platforms:
            target_dir = os.path.join(base_video_dir, platform)
            platform_download_dirs[platform] = target_dir
            Path(target_dir).mkdir(parents=True, exist_ok=True)

        return platform_download_dirs

    async def _search_platforms_parallel(
        self,
        platforms: List[str],
        platform_queries: List[str],
        recency_days: int,
        platform_download_dirs: Dict[str, str],
        job_id: str
    ) -> List[Dict[str, Any]]:
        """Search all platforms in parallel for videos.

        Args:
            platforms: List of platforms to search
            platform_queries: Queries for each platform
            recency_days: Video recency filter in days
            platform_download_dirs: Download directories per platform
            job_id: Job identifier

        Returns:
            List of video data from all platforms

        Raises:
            PlatformCrawlerError: If platform search fails
        """
        try:
            return await self.video_fetcher.search_all_platforms_videos_parallel(
                platforms=platforms,
                queries=platform_queries,
                recency_days=recency_days,
                download_dirs=platform_download_dirs,
                num_videos=config.NUM_VIDEOS,
                job_id=job_id,
                max_concurrent_platforms=config.MAX_CONCURRENT_PLATFORMS
            )
        except Exception as e:
            raise PlatformCrawlerError(
                f"Parallel platform search failed: {str(e)}",
                platform=",".join(platforms)
            )

    async def _update_job_progress(self, job_id: str, total_videos: int) -> None:
        """Update job progress for video crawling phase.

        Args:
            job_id: Job identifier
            total_videos: Total number of videos to process
        """
        if self.job_progress_manager:
            await self.job_progress_manager.update_job_progress(
                job_id, "video", total_videos, 0, "crawling"
            )

    async def _handle_zero_videos_case(self, job_id: str) -> None:
        """Handle case where no videos are found.

        Args:
            job_id: Job identifier
        """
        logger.info(f"No videos found for job {job_id}")
        if self.event_emitter:
            await self.event_emitter.publish_videos_collections_completed(job_id)
        logger.info(
            "Completed video search with zero videos",
            job_id=job_id,
            total_videos=0
        )

    async def _process_and_emit_videos(self, all_videos: List[Dict[str, Any]], job_id: str) -> None:
        """Process all videos and emit completion events.

        Args:
            all_videos: List of video data to process
            job_id: Job identifier
        """
        batch_payload: List[Dict[str, Any]] = []

        for video_data in all_videos:
            result = await self.video_processor.process_video(video_data, job_id)
            if result.get("video_id"):
                batch_payload.append(result)

        # Run automatic cleanup after video processing if enabled
        await self.cleanup_service.run_auto_cleanup(job_id)

        # Emit batch completion events
        if self.event_emitter and batch_payload:
            await self.event_emitter.publish_videos_keyframes_ready_batch(job_id, batch_payload)

        if self.event_emitter:
            await self.event_emitter.publish_videos_collections_completed(job_id)

    def _get_video_dir(self) -> str:
        """Get the video directory path.

        Returns:
            Path to video storage directory
        """
        return self._video_dir_override or config.VIDEO_DIR

    def _initialize_platform_crawlers(self) -> Dict[str, PlatformCrawlerInterface]:
        """Initialize platform crawlers for each supported platform.

        Returns:
            Dictionary mapping platform names to crawler instances
        """
        crawlers = {}

        # Use real YouTube crawler
        crawlers["youtube"] = YoutubeCrawler()

        # Use real TikTok crawler
        crawlers["tiktok"] = TikTokCrawler()

        # Use mock crawlers for other platforms (not implemented yet)
        crawlers["bilibili"] = MockPlatformCrawler("bilibili")
        crawlers["douyin"] = MockPlatformCrawler("douyin")

        return crawlers

    async def run_manual_cleanup(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run manual cleanup for debugging/testing purposes.

        Args:
            dry_run: If True, only list files without removing them

        Returns:
            Dictionary with cleanup results

        Raises:
            CleanupOperationError: If cleanup operation fails
        """
        try:
            return await self.cleanup_service.run_manual_cleanup(dry_run)
        except Exception as e:
            raise CleanupOperationError(
                f"Manual cleanup failed: {str(e)}",
                directory=self._get_video_dir()
            )


