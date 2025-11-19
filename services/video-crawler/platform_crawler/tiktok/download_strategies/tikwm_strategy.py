import asyncio
import os
import re
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from common_py.logging_config import configure_logging
from keyframe_extractor.factory import KeyframeExtractorFactory

from .base import TikTokDownloadStrategy
from ..metrics import record_download_metrics

logger = configure_logging("video-crawler:tiktok_tikwm_strategy")


class TikwmDownloadStrategy(TikTokDownloadStrategy):
    """TikTok download strategy using TikWM's public media endpoint."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)

        # TikWM configuration (hardcoded defaults as per sprint requirements)
        self.tikwm_base_url = "https://www.tikwm.com/video/media/play"
        self.max_file_size = 500 * 1024 * 1024  # 500MB (same as other strategies)
        self.download_timeout = config.get("timeout", 30)
        self.max_retries = 2  # Small retry envelope for transient HTTP failures
        self.retry_delay = 1  # seconds

        # Video storage configuration
        self.keyframe_storage_path = self.config.get("keyframe_storage_path", "./keyframes/tiktok")
        self.keyframe_extractor = KeyframeExtractorFactory.build(
            keyframe_dir=self.keyframe_storage_path,
            create_dirs=True
        )

    def download_video(self, url: str, video_id: str, output_path: str) -> Optional[str]:
        """
        Download a TikTok video using the TikWM public endpoint.

        This method is synchronous to match the strategy interface, but uses
        asyncio internally to handle the async HTTP client.
        """
        start_time = time.time()
        success = False
        error_code = None
        file_size = None
        retries = 0

        try:
            # Check if we're already in an event loop
            try:
                # We're in a running loop, we need to run in a thread to avoid blocking
                import concurrent.futures

                def run_async_in_thread():
                    # Create a new event loop in the thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            self._download_video_async_with_retries(url, video_id, output_path)
                        )
                    finally:
                        new_loop.close()
                        asyncio.set_event_loop(None)

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async_in_thread)
                    result, attempt_retries = future.result()
                    retries = attempt_retries
            except RuntimeError:
                # No running loop, safe to use asyncio.run
                result, retries = asyncio.run(
                    self._download_video_async_with_retries(url, video_id, output_path)
                )

            if result:
                success = True
                if os.path.exists(result):
                    file_size = os.path.getsize(result)

            return result

        except Exception as e:
            # Extract error code if it's one of our custom errors
            if hasattr(e, 'error_code'):
                error_code = e.error_code
            else:
                error_code = "UNKNOWN_ERROR"
            raise
        finally:
            execution_time = time.time() - start_time

            # Record metrics
            record_download_metrics(
                strategy="tikwm",
                video_id=video_id,
                url=url,
                success=success,
                error_code=error_code,
                execution_time=execution_time,
                file_size=file_size,
                retries=retries
            )

    async def _download_video_async_with_retries(
        self, url: str, video_id: str, output_path: str
    ) -> Tuple[Optional[str], int]:
        """Async implementation of video download with retry logic."""

        for attempt in range(self.max_retries + 1):
            try:
                result = await self._download_video_async(url, video_id, output_path)
                return result, attempt
            except Exception as exc:
                # Determine if this is a retryable error
                if self._is_retryable_error(exc) and attempt < self.max_retries:
                    logger.warning(
                        "TikWM download failed (attempt %d/%d), retrying in %d seconds: %s",
                        attempt + 1,
                        self.max_retries + 1,
                        self.retry_delay,
                        str(exc),
                        video_id=video_id,
                        strategy="tikwm"
                    )
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    # Not retryable or max retries reached
                    logger.error(
                        "TikWM download failed after %d attempts: %s",
                        attempt + 1,
                        str(exc),
                        video_id=video_id,
                        strategy="tikwm"
                    )
                    raise exc

        return None, self.max_retries

    def _is_retryable_error(self, exc: Exception) -> bool:
        """Determine if an error is retryable."""
        if isinstance(exc, httpx.HTTPStatusError):
            # Retry on 5xx errors
            return 500 <= exc.response.status_code < 600
        elif isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
            # Retry on network/timeout errors
            return True
        elif isinstance(exc, httpx.RequestError):
            # Retry on other request errors
            return True
        return False

    def _extract_video_id_from_url(self, url: str) -> Optional[str]:
        """Extract video ID from TikTok URL."""
        pattern = r'tiktok\.com/@[^/]+/video/(\d+)'
        match = re.search(pattern, url)
        return match.group(1) if match else None

    async def _download_video_async(self, url: str, video_id: str, output_path: str) -> Optional[str]:
        """Async implementation of video download."""
        output_filename = os.path.join(output_path, f"{video_id}.mp4")

        logger.info(
            "Starting TikTok video download via TikWM",
            video_id=video_id,
            url=url,
            output_path=output_filename,
            strategy="tikwm"
        )

        try:
            # Step 1: Extract video ID from URL
            extracted_video_id = self._extract_video_id_from_url(url)
            if not extracted_video_id:
                error = ValueError("Could not extract video ID from TikTok URL")
                error.error_code = "NO_VIDEO_ID"
                raise error

            if extracted_video_id != video_id:
                logger.warning(
                    "Video ID mismatch: extracted %s from URL but expected %s",
                    extracted_video_id,
                    video_id,
                    strategy="tikwm"
                )

            # Step 2: Build TikWM URL
            tikwm_url = f"{self.tikwm_base_url}/{extracted_video_id}.mp4"
            logger.debug(
                "Built TikWM URL: %s",
                tikwm_url,
                video_id=video_id,
                strategy="tikwm"
            )

            # Step 3: HEAD request to resolve redirects and validate
            final_url = await self._resolve_url_with_head(tikwm_url, video_id)
            if not final_url:
                return None

            # Step 4: Stream the video file
            success = await self._stream_video_file(final_url, output_filename, video_id)
            if not success:
                return None

            # Step 5: Validate the downloaded file
            if os.path.exists(output_filename):
                file_size = os.path.getsize(output_filename)
                if file_size > self.max_file_size:
                    logger.error(
                        "Downloaded file exceeds size limit",
                        video_id=video_id,
                        file_size=file_size,
                        max_size=self.max_file_size,
                        strategy="tikwm"
                    )
                    try:
                        os.remove(output_filename)
                    except Exception:
                        pass
                    error = ValueError("Downloaded file exceeds size limit")
                    error.error_code = "SIZE_LIMIT_EXCEEDED"
                    raise error
                elif file_size == 0:
                    logger.error(
                        "Downloaded file is empty",
                        video_id=video_id,
                        strategy="tikwm"
                    )
                    try:
                        os.remove(output_filename)
                    except Exception:
                        pass
                    error = ValueError("Downloaded file is empty")
                    error.error_code = "EMPTY_FILE"
                    raise error

            logger.info(
                "Successfully downloaded TikTok video via TikWM",
                video_id=video_id,
                file_size=os.path.getsize(output_filename) if os.path.exists(output_filename) else 0,
                output_filename=output_filename,
                strategy="tikwm"
            )

            return output_filename

        except Exception as exc:
            logger.error(
                "Failed to download TikTok video via TikWM",
                video_id=video_id,
                url=url,
                error=str(exc),
                strategy="tikwm"
            )

            # Clean up partial download
            if os.path.exists(output_filename):
                try:
                    os.remove(output_filename)
                except Exception:
                    pass

            # Add error code if not present
            if not hasattr(exc, 'error_code'):
                if isinstance(exc, httpx.HTTPStatusError):
                    exc.error_code = f"HTTP_{exc.response.status_code}"
                elif isinstance(exc, httpx.RequestError):
                    exc.error_code = "NETWORK_ERROR"
                else:
                    exc.error_code = "UNKNOWN_ERROR"

            raise exc

    async def _resolve_url_with_head(self, url: str, video_id: str) -> Optional[str]:
        """Perform HEAD request to resolve redirects and validate."""
        try:
            async with httpx.AsyncClient(timeout=self.download_timeout, follow_redirects=True) as client:
                response = await client.head(url)

                if response.status_code != 200:
                    logger.error(
                        "HEAD request failed",
                        video_id=video_id,
                        url=url,
                        status_code=response.status_code,
                        strategy="tikwm"
                    )
                    error = ValueError(f"HEAD request failed with status {response.status_code}")
                    error.error_code = "HEAD_FAILED"
                    raise error

                # Check content type
                content_type = response.headers.get("content-type", "")
                if not content_type.startswith("video/"):
                    logger.error(
                        "Invalid content type",
                        video_id=video_id,
                        content_type=content_type,
                        strategy="tikwm"
                    )
                    error = ValueError(f"Invalid content type: {content_type}")
                    error.error_code = "INVALID_CONTENT_TYPE"
                    raise error

                # Check content length if available
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > self.max_file_size:
                    logger.error(
                        "Content-Length exceeds size limit",
                        video_id=video_id,
                        content_length=content_length,
                        max_size=self.max_file_size,
                        strategy="tikwm"
                    )
                    error = ValueError("Content-Length exceeds size limit")
                    error.error_code = "SIZE_LIMIT_EXCEEDED"
                    raise error

                final_url = str(response.url)
                logger.debug(
                    "HEAD request successful",
                    video_id=video_id,
                    original_url=url,
                    final_url=final_url,
                    content_type=content_type,
                    content_length=content_length,
                    strategy="tikwm"
                )

                return final_url

        except Exception as exc:
            if hasattr(exc, 'error_code'):
                raise exc

            logger.error(
                "HEAD request error",
                video_id=video_id,
                url=url,
                error=str(exc),
                strategy="tikwm"
            )

            error = ValueError(f"HEAD request error: {str(exc)}")
            error.error_code = "HEAD_FAILED"
            raise error

    async def _stream_video_file(
        self,
        url: str,
        output_filename: str,
        video_id: str
    ) -> bool:
        """Stream video file from URL to local file."""
        try:
            async with httpx.AsyncClient(timeout=self.download_timeout) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()

                    # Stream to file
                    with open(output_filename, "wb") as f:
                        downloaded_bytes = 0
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                            downloaded_bytes += len(chunk)

                            # Check file size during download
                            if downloaded_bytes > self.max_file_size:
                                logger.warning(
                                    "Download exceeded size limit during streaming",
                                    video_id=video_id,
                                    current_size=downloaded_bytes,
                                    max_size=self.max_file_size,
                                    strategy="tikwm"
                                )
                                f.close()
                                try:
                                    os.remove(output_filename)
                                except Exception:
                                    pass
                                error = ValueError("Download exceeded size limit during streaming")
                                error.error_code = "SIZE_LIMIT_EXCEEDED"
                                raise error

                    logger.debug(
                        "Successfully streamed video file",
                        video_id=video_id,
                        output_filename=output_filename,
                        final_size=os.path.getsize(output_filename),
                        strategy="tikwm"
                    )
                    return True

        except httpx.HTTPStatusError as exc:
            logger.error(
                "HTTP error while streaming video",
                video_id=video_id,
                status_code=exc.response.status_code,
                url=str(exc.request.url),
                strategy="tikwm"
            )
            error = ValueError(f"HTTP error while streaming: {exc.response.status_code}")
            error.error_code = f"STREAM_ERROR_HTTP_{exc.response.status_code}"
            raise error
        except Exception as exc:
            if hasattr(exc, 'error_code'):
                raise exc

            logger.error(
                "Error while streaming video file",
                video_id=video_id,
                download_url=url,
                error=str(exc),
                strategy="tikwm"
            )
            error = ValueError(f"Stream error: {str(exc)}")
            error.error_code = "STREAM_ERROR"
            raise error

    async def extract_keyframes(
        self, video_path: str, video_id: str
    ) -> Tuple[Optional[str], List[Tuple[float, str]]]:
        """
        Extract keyframes from a downloaded TikTok video.

        This method reuses the same keyframe extraction logic as the other strategies
        to maintain consistency.
        """
        logger.info(
            "Starting keyframe extraction for video %s from: %s",
            video_id,
            video_path,
            strategy="tikwm"
        )

        keyframes_dir: Optional[str] = None
        keyframes: List[Tuple[float, str]] = []

        # Retry configuration
        max_retries = 2
        retry_delay = 1  # seconds

        for attempt in range(max_retries + 1):
            try:
                keyframes_dir = os.path.join(self.keyframe_storage_path, video_id)
                os.makedirs(keyframes_dir, exist_ok=True)

                logger.debug(
                    "Created keyframes directory: %s",
                    keyframes_dir,
                    video_id=video_id,
                    strategy="tikwm"
                )

                keyframes = await self.keyframe_extractor.extract_keyframes(
                    video_url="",  # Not available for TikWM downloads
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
                        strategy="tikwm"
                    )
                    for timestamp, frame_path in keyframes:
                        logger.debug(
                            "Extracted keyframe at timestamp %s: %s",
                            timestamp,
                            frame_path,
                            video_id=video_id,
                        )
                    return keyframes_dir, keyframes

                logger.warning(
                    "No keyframes extracted for video %s (attempt %d/%d)",
                    video_id,
                    attempt + 1,
                    max_retries + 1,
                    strategy="tikwm"
                )

                # If this is not the last attempt, wait before retrying
                if attempt < max_retries:
                    logger.info(
                        "Retrying keyframe extraction in %d seconds...",
                        retry_delay,
                        video_id=video_id,
                        strategy="tikwm"
                    )
                    await asyncio.sleep(retry_delay)
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
                    strategy="tikwm"
                )

                # If this is not the last attempt, wait before retrying
                if attempt < max_retries:
                    logger.info(
                        "Retrying keyframe extraction in %d seconds...",
                        retry_delay,
                        video_id=video_id,
                        strategy="tikwm"
                    )
                    await asyncio.sleep(retry_delay)
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
