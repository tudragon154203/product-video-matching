import uuid
import os
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import VideoCRUD, VideoFrameCRUD
from common_py.models import Video, VideoFrame
from fetcher.video_fetcher import VideoFetcher
from keyframe_extractor.length_adaptive_extractor import LengthAdaptiveKeyframeExtractor
from platform_crawler.interface import PlatformCrawlerInterface
from platform_crawler.mock_crawler import MockPlatformCrawler
from platform_crawler.youtube.youtube_crawler import YoutubeCrawler
from platform_crawler.tiktok.tiktok_crawler import TikTokCrawler
from platform_crawler.tiktok.tiktok_downloader import TikTokDownloader
from handlers.event_emitter import EventEmitter
from services.cleanup_service import cleanup_service
from common_py.logging_config import configure_logging
from config_loader import config
sys.path.append(os.path.join(os.path.dirname(__file__), "../../libs/vision-common"))
from vision_common import JobProgressManager

logger = configure_logging("video-crawler:service")


class VideoCrawlerService:
    """Main service class for mvideo crawl"""

    def __init__(self, db: DatabaseManager, broker: MessageBroker, video_dir_override: Optional[str] = None):
        self.db = db
        self.broker = broker
        self._video_dir_override = os.fspath(video_dir_override) if video_dir_override else None

        self.video_crud = VideoCRUD(db) if db else None
        self.frame_crud = VideoFrameCRUD(db) if db else None
        self.platform_crawlers = self._initialize_platform_crawlers()
        self.video_fetcher = VideoFetcher(platform_crawlers=self.platform_crawlers)
        self.keyframe_extractor = LengthAdaptiveKeyframeExtractor(create_dirs=False)
        self.event_emitter = EventEmitter(broker) if broker else None
        self.job_progress_manager = JobProgressManager(broker) if broker else None

        if config.CLEANUP_OLD_VIDEOS:
            logger.info("Video cleanup enabled with retention period of {} days".format(config.VIDEO_RETENTION_DAYS))
        else:
            logger.info("Video cleanup is disabled")

    def initialize_keyframe_extractor(self, keyframe_dir: Optional[str] = None):
        """
        Initialize the keyframe extractor with a specific directory.

        Args:
            keyframe_dir: Optional keyframe directory path. If None, creates directories using config.
        """
        if self.keyframe_extractor:
            self.keyframe_extractor = LengthAdaptiveKeyframeExtractor(
                keyframe_root_dir=keyframe_dir,
                create_dirs=True
            )

    async def handle_videos_search_request(self, event_data: Dict[str, Any]):
        """Handle video search request with cross-platform parallelism"""
        try:
            job_id = event_data["job_id"]
            industry = event_data["industry"]
            queries = event_data["queries"]
            platforms = event_data["platforms"]
            recency_days = event_data["recency_days"]

            logger.info("Processing video search request",
                        job_id=job_id, industry=industry, platforms=platforms)

            platform_queries = self._extract_platform_queries(queries, platforms)

            base_video_dir = self._get_video_dir()
            platform_download_dirs: Dict[str, str] = {}
            for platform in platforms:
                if platform == "youtube":
                    target_dir = os.path.join(base_video_dir, "youtube")
                elif platform == "tiktok":
                    target_dir = os.path.join(base_video_dir, "tiktok")
                else:
                    target_dir = os.path.join(base_video_dir, platform)

                platform_download_dirs[platform] = target_dir
                Path(target_dir).mkdir(parents=True, exist_ok=True)

            all_videos = await self.video_fetcher.search_all_platforms_videos_parallel(
                platforms=platforms,
                queries=platform_queries,
                recency_days=recency_days,
                download_dirs=platform_download_dirs,
                num_videos=config.NUM_VIDEOS,
                job_id=job_id,
                max_concurrent_platforms=config.MAX_CONCURRENT_PLATFORMS
            )

            if not all_videos:
                await self._handle_zero_videos_case(job_id)
                return

            if self.job_progress_manager:
                await self.job_progress_manager.update_job_progress(
                    job_id, "video", len(all_videos), 0, "crawling"
                )

            await self._process_and_emit_videos(all_videos, job_id)

            logger.info("Completed video search",
                        job_id=job_id,
                        total_videos=len(all_videos))

        except Exception as e:
            logger.error(f"Failed to process video search request: {str(e)}")
            raise

    def _extract_platform_queries(self, queries: Any, platforms: List[str]) -> List[str]:
        if not platforms:
            return []

        def _normalize(value: Any) -> List[str]:
            if value is None:
                return []
            if isinstance(value, str):
                return [value]
            if isinstance(value, (list, tuple, set)):
                return [item for item in value if item]
            return []

        def _dedupe_preserve_order(items: List[str]) -> List[str]:
            seen = set()
            result = []
            for item in items:
                if not item:
                    continue
                if item not in seen:
                    seen.add(item)
                    result.append(item)
            return result

        if isinstance(queries, dict):
            platforms_lower = {platform.lower() for platform in platforms}

            if platforms_lower == {"tiktok"}:
                prioritized = _normalize(queries.get("vi"))
                if prioritized:
                    return prioritized

            aggregated: List[str] = []
            for value in queries.values():
                aggregated.extend(_normalize(value))
            return _dedupe_preserve_order(aggregated)

        if isinstance(queries, str):
            return [queries]

        if isinstance(queries, (list, tuple, set)):
            return [item for item in queries if item]

        return []

    async def _handle_zero_videos_case(self, job_id: str):
        logger.info("No videos found for job {job_id}", job_id=job_id)
        if self.event_emitter:
            await self.event_emitter.publish_videos_collections_completed(job_id)
        logger.info("Completed video search with zero videos",
                    job_id=job_id,
                    total_videos=0)

    async def _process_and_emit_videos(self, all_videos: List[Dict[str, Any]], job_id: str):
        batch_payload: List[Dict[str, Any]] = []
        for video_data in all_videos:
            result = await self.process_video(video_data, job_id)
            if result.get("video_id"):
                batch_payload.append(result)

        # Run automatic cleanup after video processing if enabled
        if config.CLEANUP_OLD_VIDEOS:
            await self._run_auto_cleanup(job_id)

        if self.event_emitter and batch_payload:
            await self.event_emitter.publish_videos_keyframes_ready_batch(job_id, batch_payload)

        if self.event_emitter:
            await self.event_emitter.publish_videos_collections_completed(job_id)

    async def process_video(self, video_data: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """Process a single video and extract keyframes"""
        try:
            video = await self._create_and_save_video_record(video_data, job_id)

            # Use TikTokDownloader for TikTok videos
            if video.platform == "tiktok":
                local_path = video_data.get("local_path")

                if local_path:
                    video.local_path = local_path
                    video.has_download = True
                    keyframes_data = await self._extract_and_save_keyframes(video, video_data)
                else:
                    tiktok_config = {
                        "TIKTOK_VIDEO_STORAGE_PATH": config.TIKTOK_VIDEO_STORAGE_PATH,
                        "TIKTOK_KEYFRAME_STORAGE_PATH": config.TIKTOK_KEYFRAME_STORAGE_PATH,
                        "retries": 3,
                        "timeout": 30
                    }
                    downloader = TikTokDownloader(tiktok_config)

                    success = await downloader.orchestrate_download_and_extract(
                        url=video_data["url"],
                        video_id=video.video_id,
                        video=video,
                        db=self.db
                    )

                    if not success:
                        logger.error(f"TikTok download and extraction failed for video {video.video_id}")
                        return {
                            "video_id": None,
                            "platform": video.platform,
                            "frames": []
                        }

                    video_data["local_path"] = video.local_path
                    keyframes_data = await self._extract_and_save_keyframes(video, video_data)
            else:
                keyframes_data = await self._extract_and_save_keyframes(video, video_data)

            await self._emit_keyframes_ready_event(video, keyframes_data, job_id)

            # Increment processed count for the video
            if self.job_progress_manager:
                await self.job_progress_manager.update_job_progress(job_id, "video", 0, 1, "crawling")

            logger.info("Processed video", video_id=video.video_id,
                        frame_count=len(keyframes_data))
            return {
                "video_id": video.video_id,
                "platform": video.platform,
                "frames": keyframes_data
            }

        except Exception as e:
            logger.error(f"Failed to process video: {str(e)}", extra={"video_data": video_data})
            return {
                "video_id": None,
                "platform": video_data.get("platform"),
                "frames": []
            }

    async def _create_and_save_video_record(self, video_data: Dict[str, Any], job_id: str) -> Video:
        video = Video(
            video_id=str(uuid.uuid4()),
            platform=video_data["platform"],
            url=video_data["url"],
            title=video_data["title"],
            duration_s=video_data.get("duration_s")
        )
        await self.db.execute(
            "INSERT INTO videos (video_id, platform, url, title, duration_s, job_id) VALUES ($1, $2, $3, $4, $5, $6)",
            video.video_id, video.platform, video.url,
            video.title, video.duration_s, job_id
        )
        return video

    async def _extract_and_save_keyframes(self, video: Video, video_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Get the local path from video_data if available
        local_path = video_data.get("local_path")

        # Extract keyframes from downloaded video or create dummy frames
        keyframes = await self.keyframe_extractor.extract_keyframes(
            video_data["url"], video.video_id, local_path
        )

        frame_data = []
        for i, (timestamp, frame_path) in enumerate(keyframes):
            frame_id = f"{video.video_id}_frame_{i}"
            frame = VideoFrame(
                frame_id=frame_id,
                video_id=video.video_id,
                ts=timestamp,
                local_path=frame_path
            )
            await self.frame_crud.create_video_frame(frame)
            frame_data.append({
                "frame_id": frame_id,
                "ts": timestamp,
                "local_path": frame_path
            })
        return frame_data

    async def _extract_keyframes_from_downloader(self, downloader: TikTokDownloader, video_id: str) -> List[Dict[str, Any]]:
        """Extract keyframes data from TikTokDownloader for response formatting"""
        try:
            # Get the list of extracted keyframes from the downloader
            from keyframe_extractor.length_adaptive_extractor import LengthAdaptiveKeyframeExtractor
            extractor = LengthAdaptiveKeyframeExtractor(keyframe_root_dir=downloader.keyframe_storage_path)
            keyframes = await extractor.extract_keyframes(
                video_url="",  # Not needed for local file processing
                video_id=video_id,
                local_path=None  # Will be determined by the extractor
            )

            frame_data = []
            for i, (timestamp, frame_path) in enumerate(keyframes):
                frame_id = f"{video_id}_frame_{i}"
                frame_data.append({
                    "frame_id": frame_id,
                    "ts": timestamp,
                    "local_path": frame_path
                })
            return frame_data
        except Exception as e:
            logger.error(f"Failed to extract keyframes data from downloader for video {video_id}: {str(e)}")
            return []

    def _get_video_dir(self) -> str:
        return self._video_dir_override or config.VIDEO_DIR

    async def _emit_keyframes_ready_event(self, video: Video, keyframes_data: List[Dict[str, Any]], job_id: str):
        if keyframes_data and self.event_emitter:
            await self.event_emitter.publish_videos_keyframes_ready(
                video.video_id, keyframes_data, job_id
            )

    def _initialize_platform_crawlers(self) -> Dict[str, PlatformCrawlerInterface]:
        """Initialize platform crawlers for each supported platform"""
        crawlers = {}

        # Use real YouTube crawler
        crawlers["youtube"] = YoutubeCrawler()

        # Use real TikTok crawler
        crawlers["tiktok"] = TikTokCrawler()

        # Use mock crawlers for other platforms (not implemented yet)
        crawlers["bilibili"] = MockPlatformCrawler("bilibili")
        crawlers["douyin"] = MockPlatformCrawler("douyin")

        return crawlers

    async def _run_auto_cleanup(self, job_id: str):
        """Run automatic video cleanup after processing"""
        try:
            logger.info(f"[AUTO-CLEANUP] Starting cleanup for job {job_id}")

            # Create directory structure for cleanup based on config
            video_dir = self._get_video_dir()

            # Perform cleanup (dry run is False for actual cleanup)
            cleanup_results = await cleanup_service.perform_cleanup(video_dir, dry_run=False)

            if cleanup_results['files_removed']:
                logger.info(f"[AUTO-CLEANUP] Successfully cleaned up {len(cleanup_results['files_removed'])} files for job {job_id}")
            else:
                logger.info(f"[AUTO-CLEANUP] No files to cleanup for job {job_id}")

        except Exception as e:
            logger.error(f"[AUTO-CLEANUP-ERROR] Failed to run cleanup for job {job_id}: {str(e)}")

    async def run_manual_cleanup(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run manual cleanup for debugging/testing purposes

        Args:
            dry_run: If True, only list files without removing them

        Returns:
            Dictionary with cleanup results
        """
        try:
            logger.info(f"[MANUAL-CLEANUP] Starting cleanup (dry_run={dry_run})")

            # Get cleanup information first
            base_dir = self._get_video_dir()
            cleanup_info = await cleanup_service.get_cleanup_info(base_dir)

            # Perform cleanup
            cleanup_results = await cleanup_service.perform_cleanup(base_dir, dry_run)

            return {
                'cleanup_info': cleanup_info,
                'cleanup_results': cleanup_results,
                'config': cleanup_service.get_status()
            }

        except Exception as e:
            logger.error(f"[MANUAL-CLEANUP-ERROR] Failed to run manual cleanup: {str(e)}")
            raise
