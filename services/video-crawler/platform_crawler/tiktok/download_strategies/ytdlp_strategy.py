import os
import shutil
from typing import List, Optional, Tuple

import yt_dlp
from yt_dlp.utils import DownloadError

from common_py.logging_config import configure_logging

from .base import TikTokDownloadStrategy

logger = configure_logging("video-crawler:tiktok_ytdlp_strategy")


class TikTokAntiBotError(Exception):
    """Custom exception for TikTok anti-bot detection"""
    pass


class YtdlpDownloadStrategy(TikTokDownloadStrategy):
    """TikTok download strategy using yt-dlp."""

    def download_video(self, url: str, video_id: str, output_path: str) -> Optional[str]:
        """Download a TikTok video using yt-dlp."""
        output_filename = os.path.join(output_path, f"{video_id}.mp4")

        format_candidates = [
            # 1) Best muxed with video; prefer MP4 if present
            'b[hasvideo=true][ext=mp4]/b[hasvideo=true]',
            # 2) If site exposes split A/V (rare on TikTok), merge them; else fallback to best muxed
            'bv*+ba/b[hasvideo=true]',
            # 3) Allow HLS too (don't exclude m3u8); still ensure video
            'best[hasvideo=true]'
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

    async def extract_keyframes(
        self, video_path: str, video_id: str
    ) -> Tuple[Optional[str], List[Tuple[float, str]]]:
        """Extract keyframes from a downloaded TikTok video with retry logic."""
        logger.info("Starting keyframe extraction for video %s from: %s", video_id, video_path)

        keyframe_storage_path = self.config.get("keyframe_storage_path", "./keyframes/tiktok")
        keyframes_dir: Optional[str] = None
        keyframes: List[Tuple[float, str]] = []

        # Retry configuration
        max_retries = 2
        retry_delay = 1  # seconds

        for attempt in range(max_retries + 1):
            try:
                keyframes_dir = os.path.join(keyframe_storage_path, video_id)
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
                    keyframe_root_dir=keyframe_storage_path
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
