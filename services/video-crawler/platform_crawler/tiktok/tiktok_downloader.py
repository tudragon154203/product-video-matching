import asyncio
import inspect
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from common_py.logging_config import configure_logging

from .download_strategies.factory import TikTokDownloadStrategyFactory
from .download_strategies.ytdlp_strategy import TikTokAntiBotError

logger = configure_logging("video-crawler:tiktok_downloader")

# Optional imports for database functionality
try:
    from libs.common_py.common_py.crud.video_frame_crud import VideoFrameCRUD
    from libs.common_py.common_py.models import VideoFrame
    HAS_DB = True
except ImportError:
    HAS_DB = False


class TikTokDownloader:
    """TikTok video downloader wrapper service using pluggable download strategies."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.retries = config.get("retries", 3)
        self.timeout = config.get("timeout", 30)

        self.video_storage_path = self._resolve_storage_path(
            config.get("TIKTOK_VIDEO_STORAGE_PATH"),
            ("videos", "tiktok"),
        )
        self.keyframe_storage_path = self._resolve_storage_path(
            config.get("TIKTOK_KEYFRAME_STORAGE_PATH"),
            ("keyframes", "tiktok"),
        )

        Path(self.video_storage_path).mkdir(parents=True, exist_ok=True)
        Path(self.keyframe_storage_path).mkdir(parents=True, exist_ok=True)

        # Initialize the download strategy
        strategy_config = config.copy()
        strategy_config["keyframe_storage_path"] = self.keyframe_storage_path
        self.download_strategy = TikTokDownloadStrategyFactory.create_strategy(strategy_config)

    def _resolve_storage_path(
        self,
        configured_path: Optional[str],
        default_segments: Tuple[str, ...],
    ) -> str:
        base_temp = Path(tempfile.gettempdir())

        if configured_path:
            configured = str(configured_path)
            normalized = configured.replace("\\", "/")
            if normalized.startswith("/tmp/") or normalized.startswith("//tmp/"):
                relative = normalized.split("/tmp/", 1)[1].lstrip("/\\")
                path = base_temp / Path(relative) if relative else base_temp
            else:
                candidate = Path(configured).expanduser()
                path = candidate if candidate.is_absolute() else Path.cwd() / candidate
        else:
            path = base_temp.joinpath(*default_segments)

        path = path.resolve()
        return str(path)

    async def download_videos_batch(
        self,
        videos: Dict[str, Any],
        download_dir: str,
        max_parallel_downloads: int = 1,
    ) -> List[Dict[str, Any]]:
        """Download multiple TikTok videos in parallel."""
        if not videos:
            return []

        max_parallel = max(1, max_parallel_downloads)
        os.makedirs(download_dir, exist_ok=True)

        original_video_path = self.video_storage_path
        self.video_storage_path = download_dir

        semaphore = asyncio.Semaphore(max_parallel)
        results: List[Dict[str, Any]] = []

        download_is_async = inspect.iscoroutinefunction(self.download_video)

        async def process(video: Dict[str, Any]):
            url = video.get("webViewUrl")
            video_id = video.get("id")

            if not url or not video_id:
                logger.warning("Skipping TikTok video missing url or id", video=video)
                return None

            async with semaphore:
                try:
                    if download_is_async:
                        local_path = await self.download_video(url, video_id)  # type: ignore[arg-type]
                    else:
                        local_path = await asyncio.to_thread(self.download_video, url, video_id)
                except TikTokAntiBotError as exc:
                    logger.warning(
                        "Anti-bot blocked TikTok download",
                        video_id=video_id,
                        error=str(exc),
                    )
                    return None
                except Exception as exc:
                    logger.error(
                        "Unexpected error downloading TikTok video",
                        video_id=video_id,
                        error=str(exc),
                    )
                    return None

            if not local_path:
                logger.warning(
                    "TikTok download returned no local path",
                    video_id=video_id,
                    url=url,
                )
                return None

            return {
                "platform": self.config.get("platform_name", "tiktok"),
                "url": url,
                "title": video.get("caption"),
                "video_id": video_id,
                "author_handle": video.get("authorHandle"),
                "like_count": video.get("likeCount"),
                "upload_time": video.get("uploadTime"),
                "local_path": local_path,
                "duration_s": None,
            }

        try:
            tasks = [process(video) for video in videos.values()]
            download_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in download_results:
                if isinstance(result, dict) and result.get("local_path"):
                    results.append(result)
                elif isinstance(result, Exception):
                    logger.error("TikTok download task raised exception", error=str(result))

            logger.info(
                "TikTok batch download complete",
                requested=len(videos),
                successful=len(results),
                download_dir=download_dir,
            )
            return results
        finally:
            self.video_storage_path = original_video_path

    def download_video(self, url: str, video_id: str) -> Optional[str]:
        """Download a TikTok video using the configured strategy."""
        return self.download_strategy.download_video(url, video_id, self.video_storage_path)

    async def extract_keyframes(
        self, video_path: str, video_id: str
    ) -> Tuple[Optional[str], List[Tuple[float, str]]]:
        """Extract keyframes from a downloaded TikTok video using the configured strategy."""
        return await self.download_strategy.extract_keyframes(video_path, video_id)

    async def orchestrate_download_and_extract(
        self,
        url: str,
        video_id: str,
        video: Optional[Any] = None,
        db: Optional[Any] = None,
    ) -> bool:
        """Orchestrate video download and keyframe extraction."""
        logger.info(
            "Starting orchestration of download and extraction for video %s from URL: %s",
            video_id,
            url,
        )

        try:
            local_path = self.download_video(url, video_id)
            if not local_path:
                logger.error("Download failed for video %s", video_id)
                return False

            logger.info("Video download successful for video %s: %s", video_id, local_path)

            keyframes_dir, keyframes = await self.extract_keyframes(local_path, video_id)

            # Enhanced error handling for keyframe extraction
            if not keyframes_dir or not keyframes:
                logger.warning(
                    "Keyframe extraction returned empty results for video %s: keyframes_dir=%s, keyframes_count=%s",
                    video_id,
                    keyframes_dir,
                    len(keyframes) if keyframes else 0,
                )
                # Continue processing even if keyframe extraction fails partially

                # Try to at least return success if download worked, to not block the pipeline
                if video:
                    video.local_path = local_path
                    video.has_download = True
                    logger.debug(
                        "Updated video object for video %s with local_path (no keyframes): %s",
                        video_id,
                        local_path,
                    )
                return True  # Return True for download success, even if keyframes failed

            # Log the keyframes extraction result
            logger.info(
                "Keyframe extraction completed for video %s: %s keyframes extracted to %s",
                video_id,
                len(keyframes),
                keyframes_dir,
            )

            logger.info(
                "Keyframe extraction successful for video %s: %s",
                video_id,
                keyframes_dir,
            )

            if video:
                video.local_path = local_path
                video.has_download = True
                logger.debug(
                    "Updated video object for video %s with local_path: %s",
                    video_id,
                    local_path,
                )

            if db and HAS_DB and keyframes:
                await self._persist_keyframes(video_id, keyframes, db)
            elif not HAS_DB:
                logger.info("Database persistence skipped - libs.common_py not available")

            logger.info("Successfully completed orchestration for video %s", video_id)
            return True

        except TikTokAntiBotError as exc:
            logger.error("Anti-bot error in orchestration for video %s: %s", video_id, exc)
            return False
        except Exception as exc:
            logger.error(
                "Unexpected error in orchestration for video %s: %s",
                video_id,
                exc,
            )
            return False

    async def _persist_keyframes(
        self,
        video_id: str,
        keyframes: List[Tuple[float, str]],
        db: Any,
    ) -> None:
        try:
            video_frame_crud = VideoFrameCRUD(db)
            persisted_count = 0
            for index, (timestamp, frame_path) in enumerate(keyframes):
                frame = VideoFrame(
                    frame_id=f"{video_id}_frame_{index}",
                    video_id=video_id,
                    ts=timestamp,
                    local_path=frame_path,
                )
                try:
                    await video_frame_crud.create_video_frame(frame)
                    persisted_count += 1
                    logger.debug(
                        "Persisted keyframe metadata for video %s, timestamp %s",
                        video_id,
                        timestamp,
                    )
                except Exception as frame_error:
                    logger.warning(
                        "Failed to persist keyframe metadata for video %s, timestamp %s: %s",
                        video_id,
                        timestamp,
                        frame_error,
                    )

            if hasattr(db, "commit"):
                db.commit()
                logger.info(
                    "Successfully committed %s keyframes to database for video %s",
                    persisted_count,
                    video_id,
                )
            else:
                logger.info(
                    "Successfully created %s keyframes in database for video %s",
                    persisted_count,
                    video_id,
                )
        except Exception as db_error:
            logger.warning(
                "Failed to persist keyframes to database for video %s: %s",
                video_id,
                db_error,
            )
            if hasattr(db, "commit"):
                try:
                    db.commit()
                except Exception:
                    pass
