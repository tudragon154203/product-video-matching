"""Video processing workflow separated from main service."""

import uuid
from typing import Any, Dict, List, Optional

from common_py.crud import VideoCRUD, VideoFrameCRUD
from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging
from common_py.models import Video, VideoFrame
from config_loader import config
from handlers.event_emitter import EventEmitter
from keyframe_extractor.length_adaptive_extractor import LengthAdaptiveKeyframeExtractor
from platform_crawler.tiktok.tiktok_downloader import TikTokDownloader
from services.exceptions import VideoProcessingError, VideoDownloadError, DatabaseOperationError
from vision_common import JobProgressManager

logger = configure_logging("video-crawler:video_processor")


class VideoProcessor:
    """Handles video processing workflow including keyframe extraction."""

    def __init__(
        self,
        db: DatabaseManager,
        event_emitter: Optional[EventEmitter] = None,
        job_progress_manager: Optional[JobProgressManager] = None,
        video_dir_override: Optional[str] = None
    ):
        self.db = db
        self.event_emitter = event_emitter
        self.job_progress_manager = job_progress_manager
        self._video_dir_override = video_dir_override

        self.video_crud = VideoCRUD(db) if db else None
        self.frame_crud = VideoFrameCRUD(db) if db else None
        self.keyframe_extractor = LengthAdaptiveKeyframeExtractor(create_dirs=False)

    async def process_video(self, video_data: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """Process a single video and extract keyframes.

        Args:
            video_data: Video metadata and URLs
            job_id: Job identifier for tracking

        Returns:
            Processing result with video_id and frame data
        """
        try:
            video = await self._create_and_save_video_record(video_data, job_id)

            # Handle platform-specific processing
            if video.platform == "tiktok":
                keyframes_data = await self._process_tiktok_video(video, video_data)
            else:
                keyframes_data = await self._process_standard_video(video, video_data)

            await self._emit_keyframes_ready_event(video, keyframes_data, job_id)
            await self._update_progress(job_id)

            logger.info(
                "Processed video",
                video_id=video.video_id,
                frame_count=len(keyframes_data)
            )

            return {
                "video_id": video.video_id,
                "platform": video.platform,
                "frames": keyframes_data
            }

        except Exception as e:
            logger.error(
                f"Failed to process video: {str(e)}",
                extra={"video_data": video_data}
            )
            return {
                "video_id": None,
                "platform": video_data.get("platform"),
                "frames": []
            }

    async def _process_tiktok_video(self, video: Video, video_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process TikTok video with specialized downloader."""
        local_path = video_data.get("local_path")

        if local_path:
            # Video already downloaded, just update record
            video.local_path = local_path
            video.has_download = True
            return []  # Keyframes already extracted

        # Use TikTokDownloader for download and extraction
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
            return []

        video_data["local_path"] = video.local_path
        return []  # Keyframes extracted by downloader

    async def _process_standard_video(self, video: Video, video_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process standard video (YouTube, etc.) with keyframe extraction."""
        local_path = video_data.get("local_path")

        keyframes = await self.keyframe_extractor.extract_keyframes(
            video_data.get("url", ""),
            video.video_id,
            local_path
        )

        return await self._save_keyframes(keyframes, video.video_id)

    async def _create_and_save_video_record(self, video_data: Dict[str, Any], job_id: str) -> Video:
        """Create and save video record to database."""
        video = Video(
            video_id=str(uuid.uuid4()),
            platform=video_data["platform"],
            url=video_data["url"],
            title=video_data["title"],
            duration_s=video_data.get("duration_s")
        )

        await self.db.execute(
            "INSERT INTO videos (video_id, platform, url, title, duration_s, job_id) "
            "VALUES ($1, $2, $3, $4, $5, $6)",
            video.video_id,
            video.platform,
            video.url,
            video.title,
            video.duration_s,
            job_id
        )

        return video

    async def _save_keyframes(self, keyframes: List[tuple], video_id: str) -> List[Dict[str, Any]]:
        """Save keyframes to database and return frame data."""
        frame_data = []
        for i, (timestamp, frame_path) in enumerate(keyframes):
            frame_id = f"{video_id}_frame_{i}"
            frame = VideoFrame(
                frame_id=frame_id,
                video_id=video_id,
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

    async def _emit_keyframes_ready_event(
        self,
        video: Video,
        keyframes_data: List[Dict[str, Any]],
        job_id: str
    ) -> None:
        """Emit keyframes ready event if available."""
        if keyframes_data and self.event_emitter:
            await self.event_emitter.publish_videos_keyframes_ready(
                video.video_id,
                keyframes_data,
                job_id
            )

    async def _update_progress(self, job_id: str) -> None:
        """Update job progress for processed video."""
        if self.job_progress_manager:
            await self.job_progress_manager.update_job_progress(
                job_id,
                "video",
                0,
                1,
                "crawling"
            )

    def initialize_keyframe_extractor(self, keyframe_dir: Optional[str] = None) -> None:
        """Initialize keyframe extractor with specific directory."""
        self.keyframe_extractor = LengthAdaptiveKeyframeExtractor(
            keyframe_root_dir=keyframe_dir,
            create_dirs=True
        )