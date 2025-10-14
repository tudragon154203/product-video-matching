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
            # Video already downloaded, just update record and extract keyframes
            video.local_path = local_path
            video.has_download = True
            # Extract keyframes from existing local file
            try:
                keyframes = await self.keyframe_extractor.extract_keyframes(
                    video_url="",
                    video_id=video.video_id,
                    local_path=local_path
                )
                return await self._save_keyframes(keyframes, video.video_id)
            except Exception as e:
                logger.error(f"Failed to extract keyframes from existing video {video.video_id}: {e}")
                return []

        # Use TikTokDownloader for download and extraction
        tiktok_config = {
            "TIKTOK_VIDEO_STORAGE_PATH": config.TIKTOK_VIDEO_STORAGE_PATH,
            "TIKTOK_KEYFRAME_STORAGE_PATH": config.TIKTOK_KEYFRAME_STORAGE_PATH,
            "TIKTOK_CRAWL_HOST": config.TIKTOK_CRAWL_HOST,
            "TIKTOK_CRAWL_HOST_PORT": config.TIKTOK_CRAWL_HOST_PORT,
            "TIKTOK_DOWNLOAD_STRATEGY": config.TIKTOK_DOWNLOAD_STRATEGY,
            "TIKTOK_DOWNLOAD_TIMEOUT": config.TIKTOK_DOWNLOAD_TIMEOUT,
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

        logger.info(f"TikTok download and extraction result for video {video.video_id}: success={success}")

        if not success:
            logger.error(f"TikTok download and extraction failed for video {video.video_id}")
            return []

        video_data["local_path"] = video.local_path

        # Keyframes were extracted by downloader and persisted to DB
        # We need to fetch them back from the database to return them
        try:
            if self.frame_crud:
                frames = await self.frame_crud.list_video_frames(video.video_id)
                logger.info(f"Found {len(frames)} frames for video {video.video_id} in database")

                if frames:
                    return [{
                        "frame_id": frame.frame_id,
                        "ts": frame.ts,
                        "local_path": frame.local_path
                    } for frame in frames]
                else:
                    # Fallback: Try to extract keyframes directly if downloader didn't provide any
                    logger.warning(f"No frames found in database for video {video.video_id}, attempting fallback extraction")
                    if video.local_path:
                        try:
                            keyframes = await self.keyframe_extractor.extract_keyframes(
                                video_url="",
                                video_id=video.video_id,
                                local_path=video.local_path
                            )
                            if keyframes:
                                logger.info(f"Fallback extraction successful for video {video.video_id}: {len(keyframes)} keyframes")
                                return await self._save_keyframes(keyframes, video.video_id)
                            else:
                                logger.warning(f"Fallback extraction also returned no keyframes for video {video.video_id}")
                        except Exception as fallback_error:
                            logger.error(f"Fallback keyframe extraction failed for video {video.video_id}: {fallback_error}")

                    return []
        except Exception as e:
            logger.error(f"Failed to fetch keyframes for video {video.video_id} from database: {e}")
            return []

    async def _process_standard_video(self, video: Video, video_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process standard video (YouTube, etc.) with keyframe extraction."""
        local_path = video_data.get("local_path")

        keyframes = await self.keyframe_extractor.extract_keyframes(
            video_url=video_data.get("url", ""),
            video_id=video.video_id,
            local_path=local_path
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