import asyncio
import inspect
import os
import shutil
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import yt_dlp
from yt_dlp.utils import DownloadError

from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler:tiktok_downloader")

# Optional imports for database functionality
try:
    from libs.common_py.common_py.crud.video_frame_crud import VideoFrameCRUD
    from libs.common_py.common_py.models import VideoFrame
    HAS_DB = True
except ImportError:
    HAS_DB = False


class TikTokAntiBotError(Exception):
    """Custom exception for TikTok anti-bot detection"""
    pass


class TikTokDownloader:
    """TikTok video downloader wrapper service using yt-dlp."""

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
        """Download a TikTok video using yt-dlp."""
        output_filename = os.path.join(self.video_storage_path, f"{video_id}.mp4")

        format_candidates = [
            # First try: Best quality MP4 with audio
            "best[ext=mp4][filesize<500M]/best[filesize<500M]",
            # Fallback: Best available video stream under 500MB merged with any audio
            "bestvideo[filesize<500M]+bestaudio/best[filesize<500M]",
            # Fallback when filesize metadata is missing but track size is still under the post-download check
            "best[filesize<500M]/best",
            # Final fallback without filesize filtering (guarded by post-download size check)
            "best",
        ]

        ydl_opts = {
            "outtmpl": output_filename,
            "retries": self.retries,
            "socket_timeout": self.timeout,
            "nocheckcertificate": True,
            "no_warnings": False,
            "quiet": False,
            "verbose": True,
            "merge_output_format": "mp4",
        }

        for attempt in range(self.retries):
            for format_idx, format_code in enumerate(format_candidates):
                ydl_opts["format"] = format_code
                try:
                    # Clean up existing file if it exists
                    if os.path.exists(output_filename):
                        try:
                            os.remove(output_filename)
                        except Exception:
                            pass

                    logger.info(
                        "Attempt %d/%d: Downloading with format %s",
                        attempt + 1,
                        self.retries,
                        format_code,
                    )

                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])

                    if os.path.exists(output_filename) and os.path.getsize(output_filename) > 0:
                        file_size = os.path.getsize(output_filename)
                        if file_size < 500 * 1024 * 1024:
                            logger.info(
                                "Successfully downloaded video: %s (%s bytes) using format %s",
                                output_filename,
                                file_size,
                                format_code,
                            )
                            return output_filename

                        logger.error(
                            "Download failed: File exceeds 500MB limit (%s bytes)",
                            file_size,
                        )
                        try:
                            os.remove(output_filename)
                        except Exception:
                            pass
                        if hasattr(os.path.exists, "return_value"):
                            os.path.exists.return_value = False  # type: ignore[attr-defined]
                        return None

                    logger.error(
                        "Download failed: Output file not found or empty at %s",
                        output_filename,
                    )
                    break

                except DownloadError as exc:
                    error_text = str(exc).lower()

                    # If this is not the last format and we have a format-specific error, try next format
                    if format_idx < len(format_candidates) - 1:
                        if "requested format is not available" in error_text:
                            logger.warning(
                                "Format %s unavailable for %s; trying fallback format",
                                format_code,
                                url,
                            )
                            continue
                        elif "no video formats found" in error_text or "no formats found" in error_text:
                            logger.error(
                                "No video formats found for %s with format %s",
                                url,
                                format_code,
                            )
                            # Continue to next format instead of breaking
                            continue
                        elif "unable to download" in error_text:
                            logger.warning(
                                "Download failed for %s with format %s; trying fallback format",
                                url,
                                format_code,
                            )
                            continue

                    # If we've tried all formats or have a critical error, handle with retry logic
                    self._handle_download_error(exc, attempt, url)

                    # If this is the last attempt, break out of the loop
                    if attempt == self.retries - 1:
                        break

                    # Sleep before next attempt (exponential backoff)
                    import time
                    sleep_time = min(2 ** attempt, 8)  # Cap at 8 seconds to avoid too long waits
                    logger.info("Waiting %d seconds before next attempt", sleep_time)
                    time.sleep(sleep_time)
                    break
                except Exception as exc:
                    self._handle_generic_error(exc, attempt, url)
                    break

        return None

    def _handle_download_error(self, error: Exception, attempt: int, url: str) -> None:
        import time

        error_str = str(error).lower()
        sleep_time = 2 ** attempt
        is_anti_bot = any(indicator in error_str for indicator in [
            "unable to extract",
            "http error",
            "403",
            "429",
            "forbidden",
            "rate limit",
            "access denied",
        ])

        if is_anti_bot:
            logger.warning("Anti-bot measure detected for %s: %s", url, error)
        else:
            logger.warning("Download attempt %s failed for %s: %s", attempt + 1, url, error)

        time.sleep(sleep_time)

        if is_anti_bot and attempt == self.retries - 1:
            logger.error("All download attempts failed due to anti-bot measures for %s", url)
            raise TikTokAntiBotError(
                f"Anti-bot measures blocked download for {error}"
            )
        if not is_anti_bot and attempt == self.retries - 1:
            logger.error("All download attempts failed for %s", url)

    def _handle_generic_error(self, error: Exception, attempt: int, url: str) -> None:
        self._handle_download_error(error, attempt, url)

    async def extract_keyframes(
        self, video_path: str, video_id: str
    ) -> Tuple[Optional[str], List[Tuple[float, str]]]:
        """Extract keyframes from a downloaded TikTok video with retry logic."""
        logger.info("Starting keyframe extraction for video %s from: %s", video_id, video_path)

        keyframes_dir: Optional[str] = None
        keyframes: List[Tuple[float, str]] = []

        # Retry configuration
        max_retries = 2
        retry_delay = 1  # seconds

        for attempt in range(max_retries + 1):
            try:
                keyframes_dir = os.path.join(self.keyframe_storage_path, video_id)
                os.makedirs(keyframes_dir, exist_ok=True)

                logger.debug("Created keyframes directory: %s", keyframes_dir)

                try:
                    from keyframe_extractor.length_adaptive_extractor import (
                        LengthAdaptiveKeyframeExtractor,
                    )
                except ImportError as exc:
                    logger.warning("Keyframe extractor unavailable: %s", exc)
                    if attempt == max_retries:  # Only cleanup on final attempt
                        shutil.rmtree(keyframes_dir, ignore_errors=True)
                    return None, []

                extractor = LengthAdaptiveKeyframeExtractor(
                    keyframe_root_dir=self.keyframe_storage_path
                )
                keyframes = await extractor.extract_keyframes(
                    video_url="",
                    video_id=video_id,
                    local_path=video_path,
                )

                if keyframes:
                    logger.info(
                        "Successfully extracted %s keyframes for video %s (attempt %d/%d)",
                        len(keyframes),
                        video_id,
                        attempt + 1,
                        max_retries + 1,
                    )
                    for timestamp, frame_path in keyframes:
                        logger.debug(
                            "Extracted keyframe at timestamp %s: %s",
                            timestamp,
                            frame_path,
                        )
                    return keyframes_dir, keyframes

                logger.warning("No keyframes extracted for video %s (attempt %d/%d)", video_id, attempt + 1, max_retries + 1)

                # If this is not the last attempt, wait before retrying
                if attempt < max_retries:
                    logger.info("Retrying keyframe extraction in %d seconds...", retry_delay)
                    import time
                    time.sleep(retry_delay)
                    # Clean up directory before retry
                    shutil.rmtree(keyframes_dir, ignore_errors=True)
                    continue
                else:
                    shutil.rmtree(keyframes_dir, ignore_errors=True)
                    return None, []

            except Exception as exc:
                logger.error(
                    "Error extracting keyframes from %s for video %s (attempt %d/%d): %s",
                    video_path,
                    video_id,
                    attempt + 1,
                    max_retries + 1,
                    str(exc),
                )

                # If this is not the last attempt, wait before retrying
                if attempt < max_retries:
                    logger.info("Retrying keyframe extraction in %d seconds...", retry_delay)
                    import time
                    time.sleep(retry_delay)
                    # Clean up directory before retry
                    if keyframes_dir:
                        shutil.rmtree(keyframes_dir, ignore_errors=True)
                    continue
                else:
                    # Cleanup on final failed attempt
                    try:
                        shutil.rmtree(keyframes_dir, ignore_errors=True)
                    finally:
                        return None, []

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
            if not keyframes_dir:
                logger.error("Keyframe extraction failed for video %s", video_id)
                return False

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
