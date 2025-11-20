import os
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from common_py.logging_config import configure_logging
from keyframe_extractor.router import build_keyframe_extractor

from .base import TikTokDownloadStrategy
from ..metrics import record_download_metrics

logger = configure_logging("video-crawler:tiktok_scrapling_api_strategy")


class ScraplingApiDownloadStrategy(TikTokDownloadStrategy):
    """TikTok download strategy using the Scrapling API endpoint."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)

        # API configuration
        self.api_host = config.get("TIKTOK_CRAWL_HOST", "localhost")
        self.api_port = config.get("TIKTOK_CRAWL_HOST_PORT", "5680")
        self.api_timeout = config.get("TIKTOK_DOWNLOAD_TIMEOUT", 180)

        # Video processing limits (same as yt-dlp strategy)
        self.max_file_size = 500 * 1024 * 1024  # 500MB

        # Initialize client on demand
        self._client = None
        self.keyframe_storage_path = (
            config.get("keyframe_storage_path") or
            config.get("TIKTOK_KEYFRAME_STORAGE_PATH") or
            "./keyframes/tiktok"
        )
        self.keyframe_extractor = build_keyframe_extractor(
            keyframe_dir=self.keyframe_storage_path,
            create_dirs=True
        )

    @property
    def client(self):
        """Lazy initialization of the download client."""
        if self._client is None:
            from ..tiktok_download_client import TikTokDownloadClient
            self._client = TikTokDownloadClient(
                host=self.api_host,
                port=self.api_port,
                timeout=self.api_timeout
            )
        return self._client

    async def close(self) -> None:
        """Close the download client."""
        if self._client:
            await self._client.close()
            self._client = None

    def download_video(self, url: str, video_id: str, output_path: str) -> Optional[str]:
        """
        Download a TikTok video using the Scrapling API.

        This method is synchronous to match the strategy interface, but uses
        asyncio internally to handle the async HTTP client.
        """
        import asyncio

        start_time = time.time()
        success = False
        error_code = None
        file_size = None
        api_execution_time = None

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
                        return new_loop.run_until_complete(self._download_video_async(url, video_id, output_path))
                    finally:
                        new_loop.close()
                        asyncio.set_event_loop(None)

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async_in_thread)
                    result, api_exec_time = future.result()
            except RuntimeError:
                # No running loop, safe to use asyncio.run
                result, api_exec_time = asyncio.run(self._download_video_async(url, video_id, output_path))

            if result:
                success = True
                api_execution_time = api_exec_time
                if os.path.exists(result):
                    file_size = os.path.getsize(result)

            return result
        except Exception as e:
            # Extract error code if it's a TikTokDownloadError
            if hasattr(e, 'error_code'):
                error_code = e.error_code
            else:
                error_code = "UNKNOWN_ERROR"
            raise
        finally:
            execution_time = time.time() - start_time

            # Record metrics
            record_download_metrics(
                strategy="scrapling-api",
                video_id=video_id,
                url=url,
                success=success,
                error_code=error_code,
                execution_time=execution_time,
                file_size=file_size,
                api_execution_time=api_execution_time
            )

    async def _download_video_async(self, url: str, video_id: str, output_path: str) -> Optional[str]:
        """Async implementation of video download."""
        output_filename = os.path.join(output_path, f"{video_id}.mp4")
        api_execution_time = None

        logger.info(
            "Starting TikTok video download via Scrapling API",
            video_id=video_id,
            url=url,
            output_path=output_filename,
            strategy="scrapling-api"
        )

        try:
            # Resolve download URL with retry logic
            api_response = await self.client.download_video_with_retry(url)

            if not api_response.download_url:
                logger.error(
                    "No download URL returned from API",
                    video_id=video_id,
                    error_code=api_response.error_code
                )
                return None, api_execution_time

            # Store API execution time for metrics
            api_execution_time = api_response.execution_time

            # Download the video file
            success = await self._stream_video_file(
                api_response.download_url,
                output_filename,
                video_id
            )

            if not success:
                return None, api_execution_time

            # Validate file size
            if os.path.exists(output_filename):
                file_size = os.path.getsize(output_filename)
                if file_size > self.max_file_size:
                    logger.error(
                        "Downloaded file exceeds size limit",
                        video_id=video_id,
                        file_size=file_size,
                        max_size=self.max_file_size
                    )
                    try:
                        os.remove(output_filename)
                    except Exception:
                        pass
                    return None, api_execution_time
                elif file_size == 0:
                    logger.error("Downloaded file is empty", video_id=video_id)
                    try:
                        os.remove(output_filename)
                    except Exception:
                        pass
                    return None, api_execution_time

            logger.info(
                "Successfully downloaded TikTok video via Scrapling API",
                video_id=video_id,
                file_size=os.path.getsize(output_filename) if os.path.exists(output_filename) else 0,
                execution_time=api_response.execution_time,
                api_file_size=api_response.file_size
            )

            return output_filename, api_execution_time

        except Exception as exc:
            logger.error(
                "Failed to download TikTok video via Scrapling API",
                video_id=video_id,
                url=url,
                error=str(exc),
                strategy="scrapling-api"
            )

            # Clean up partial download
            if os.path.exists(output_filename):
                try:
                    os.remove(output_filename)
                except Exception:
                    pass

            return None, api_execution_time
        finally:
            # Ensure we don't keep an event-loop-bound HTTP client alive between calls.
            if self._client:
                try:
                    await self._client.close()
                except Exception:
                    logger.debug(
                        "Failed to close TikTok download client after request.",
                        exc_info=True
                    )
                finally:
                    self._client = None

    async def _stream_video_file(
        self,
        download_url: str,
        output_filename: str,
        video_id: str
    ) -> bool:
        """Stream video file from download URL to local file."""
        try:
            async with httpx.AsyncClient(timeout=self.api_timeout) as client:
                async with client.stream("GET", download_url) as response:
                    response.raise_for_status()

                    # Check content length if available
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self.max_file_size:
                        logger.warning(
                            "Content-Length exceeds size limit, skipping download",
                            video_id=video_id,
                            content_length=content_length,
                            max_size=self.max_file_size
                        )
                        return False

                    # Stream to file
                    with open(output_filename, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)

                            # Check file size during download
                            if f.tell() > self.max_file_size:
                                logger.warning(
                                    "Download exceeded size limit during streaming",
                                    video_id=video_id,
                                    current_size=f.tell(),
                                    max_size=self.max_file_size
                                )
                                f.close()
                                try:
                                    os.remove(output_filename)
                                except Exception:
                                    pass
                                return False

                    logger.info(
                        "Successfully streamed video file",
                        video_id=video_id,
                        output_filename=output_filename,
                        final_size=os.path.getsize(output_filename)
                    )
                    return True

        except httpx.HTTPStatusError as exc:
            logger.error(
                "HTTP error while streaming video",
                video_id=video_id,
                status_code=exc.response.status_code,
                url=str(exc.request.url)
            )
            return False
        except Exception as exc:
            logger.error(
                "Error while streaming video file",
                video_id=video_id,
                download_url=download_url,
                error=str(exc)
            )
            return False

    async def extract_keyframes(
        self, video_path: str, video_id: str
    ) -> Tuple[Optional[str], List[Tuple[float, str]]]:
        """
        Extract keyframes from a downloaded TikTok video.

        This method reuses the same keyframe extraction logic as the yt-dlp strategy
        to maintain consistency.
        """
        logger.info(
            "Starting keyframe extraction for video %s from: %s",
            video_id,
            video_path,
            strategy="scrapling-api"
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

                logger.debug("Created keyframes directory: %s", keyframes_dir)
                keyframes = await self.keyframe_extractor.extract_keyframes(
                    video_url="",  # Not available for API downloads
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
                        strategy="scrapling-api"
                    )
                    for timestamp, frame_path in keyframes:
                        logger.debug(
                            "Extracted keyframe at timestamp %s: %s",
                            timestamp,
                            frame_path,
                        )
                    return keyframes_dir, keyframes

                logger.warning(
                    "No keyframes extracted for video %s (attempt %d/%d)",
                    video_id,
                    attempt + 1,
                    max_retries + 1,
                    strategy="scrapling-api"
                )

                # If this is not the last attempt, wait before retrying
                if attempt < max_retries:
                    logger.info(
                        "Retrying keyframe extraction in %d seconds...",
                        retry_delay,
                        strategy="scrapling-api"
                    )
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
                    strategy="scrapling-api"
                )

                # If this is not the last attempt, wait before retrying
                if attempt < max_retries:
                    logger.info(
                        "Retrying keyframe extraction in %d seconds...",
                        retry_delay,
                        strategy="scrapling-api"
                    )
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
