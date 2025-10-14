"""
Async HTTP client for the TikTok download API.
"""
import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urljoin

import httpx
from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler:tiktok_download_client")


@dataclass
class TikTokDownloadRequest:
    """Request payload for TikTok download API."""
    url: str
    force_headful: bool = False


@dataclass
class TikTokVideoInfo:
    """Video metadata from TikTok download API response."""
    id: str
    title: str
    author: str
    duration: float
    thumbnail_url: Optional[str] = None


@dataclass
class TikTokDownloadResponse:
    """Response from TikTok download API."""
    status: str
    message: str
    download_url: Optional[str] = None
    video_info: Optional[TikTokVideoInfo] = None
    file_size: Optional[int] = None
    execution_time: Optional[float] = None
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class TikTokDownloadError(Exception):
    """Base exception for TikTok download API errors."""

    def __init__(self, message: str, error_code: Optional[str] = None, execution_time: Optional[float] = None):
        super().__init__(message)
        self.error_code = error_code
        self.execution_time = execution_time


class TikTokInvalidUrlError(TikTokDownloadError):
    """Raised when the TikTok URL is invalid."""
    pass


class TikTokNavigationError(TikTokDownloadError):
    """Raised when browser navigation fails."""
    pass


class TikTokNoDownloadLinkError(TikTokDownloadError):
    """Raised when no download link can be resolved."""
    pass


class TikTokDownloadFailedError(TikTokDownloadError):
    """Raised when the download process fails."""
    pass


class TikTokInvalidVideoError(TikTokDownloadError):
    """Raised when the video is invalid or inaccessible."""
    pass


class TikTokDownloadClient:
    """Async HTTP client for the TikTok download API."""

    # Mapping of error codes to exceptions
    ERROR_MAPPING = {
        "INVALID_URL": TikTokInvalidUrlError,
        "INVALID_VIDEO_ID": TikTokInvalidUrlError,
        "NAVIGATION_FAILED": TikTokNavigationError,
        "NO_DOWNLOAD_LINK": TikTokNoDownloadLinkError,
        "DOWNLOAD_FAILED": TikTokDownloadFailedError,
        "INVALID_VIDEO": TikTokInvalidVideoError,
    }

    # Errors that should trigger a headful retry
    HEADFUL_RETRY_ERRORS = {
        "NAVIGATION_FAILED",
        "NO_DOWNLOAD_LINK",
        "DOWNLOAD_FAILED",
    }

    def __init__(self, host: str = "localhost", port: str = "5680", timeout: int = 180):
        """
        Initialize the TikTok download client.

        Args:
            host: TikTok API host
            port: TikTok API port
            timeout: Request timeout in seconds
        """
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _parse_video_info(self, video_info_dict: Dict[str, Any]) -> TikTokVideoInfo:
        """Parse video info from API response."""
        duration = video_info_dict.get("duration")
        # Handle None duration by converting to 0.0
        if duration is None:
            duration = 0.0
        else:
            duration = float(duration)

        return TikTokVideoInfo(
            id=video_info_dict.get("id", ""),
            title=video_info_dict.get("title", ""),
            author=video_info_dict.get("author", ""),
            duration=duration,
            thumbnail_url=video_info_dict.get("thumbnail_url")
        )

    def _parse_response(self, response_data: Dict[str, Any]) -> TikTokDownloadResponse:
        """Parse API response."""
        video_info = None
        if response_data.get("video_info"):
            video_info = self._parse_video_info(response_data["video_info"])

        return TikTokDownloadResponse(
            status=response_data["status"],
            message=response_data["message"],
            download_url=response_data.get("download_url"),
            video_info=video_info,
            file_size=response_data.get("file_size"),
            execution_time=response_data.get("execution_time"),
            error_code=response_data.get("error_code"),
            error_details=response_data.get("error_details")
        )

    def _create_exception(self, response: TikTokDownloadResponse) -> TikTokDownloadError:
        """Create appropriate exception based on error code."""
        error_code = response.error_code
        message = response.message

        exception_class = self.ERROR_MAPPING.get(error_code, TikTokDownloadError)
        return exception_class(message, error_code, response.execution_time)

    async def resolve_download(
        self,
        url: str,
        force_headful: bool = False
    ) -> Tuple[TikTokDownloadResponse, bool]:
        """
        Resolve download URL for a TikTok video.

        Args:
            url: TikTok video URL
            force_headful: Force headful browser mode

        Returns:
            Tuple of (response, should_retry_with_headful)

        Raises:
            TikTokDownloadError: For API errors
            httpx.HTTPError: For network errors
        """
        api_url = urljoin(self.base_url, "/tiktok/download")
        request = TikTokDownloadRequest(url=url, force_headful=force_headful)

        payload = {
            "url": request.url,
            "force_headful": request.force_headful
        }

        logger.info(
            "Resolving TikTok download URL",
            url=url,
            force_headful=force_headful,
            api_url=api_url
        )

        try:
            response = await self.client.post(api_url, json=payload)
            response.raise_for_status()

            response_data = response.json()
            parsed_response = self._parse_response(response_data)

            logger.info(
                "TikTok download API response received",
                status=parsed_response.status,
                execution_time=parsed_response.execution_time,
                file_size=parsed_response.file_size,
                error_code=parsed_response.error_code
            )

            if parsed_response.status == "error":
                # Determine if this error should trigger a headful retry
                should_retry = (
                    not force_headful and
                    parsed_response.error_code in self.HEADFUL_RETRY_ERRORS
                )

                if should_retry:
                    logger.info(
                        "Error may be resolved with headful mode",
                        error_code=parsed_response.error_code,
                        will_retry=True
                    )
                else:
                    # Raise the appropriate exception
                    raise self._create_exception(parsed_response)

                return parsed_response, should_retry

            # Success case
            return parsed_response, False

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error from TikTok download API",
                status_code=e.response.status_code,
                url=str(e.request.url),
                error=str(e)
            )
            # For 5xx errors, we should retry with headful
            if e.response.status_code >= 500 and not force_headful:
                return TikTokDownloadResponse(
                    status="error",
                    message=f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
                    error_code="HTTP_ERROR"
                ), True
            raise

        except httpx.RequestError as e:
            logger.error(
                "Network error calling TikTok download API",
                url=str(e.request.url) if hasattr(e, 'request') else 'unknown',
                error=str(e)
            )
            # For network errors, we should retry with headful
            if not force_headful:
                return TikTokDownloadResponse(
                    status="error",
                    message=f"Network error: {str(e)}",
                    error_code="NETWORK_ERROR"
                ), True
            raise

        except Exception as e:
            logger.error(
                "Unexpected error in TikTok download client",
                url=url,
                error=str(e)
            )
            raise

    async def download_video_with_retry(
        self,
        url: str,
        max_retries: int = 1
    ) -> TikTokDownloadResponse:
        """
        Download video with automatic headful retry logic.

        Args:
            url: TikTok video URL
            max_retries: Maximum number of retries (only 1 retry with headful is supported)

        Returns:
            Successful download response

        Raises:
            TikTokDownloadError: If all retries are exhausted
        """
        # First attempt: headless
        try:
            response, should_retry = await self.resolve_download(url, force_headful=False)
            if response.status == "success":
                return response
            elif should_retry and max_retries > 0:
                logger.info("Retrying with headful mode", url=url)
        except TikTokDownloadError as e:
            if max_retries > 0 and e.error_code in self.HEADFUL_RETRY_ERRORS:
                logger.info("Retrying with headful mode after error", url=url, error_code=e.error_code)
            else:
                raise

        # Retry with headful mode if configured
        if max_retries > 0:
            try:
                response, should_retry = await self.resolve_download(url, force_headful=True)
                if response.status == "success":
                    logger.info("Headful retry succeeded", url=url)
                    return response
                else:
                    # Final attempt failed, raise the error
                    raise self._create_exception(response)
            except TikTokDownloadError as e:
                logger.error("Headful retry failed", url=url, error_code=e.error_code)
                raise
            except Exception as e:
                logger.error("Unexpected error in headful retry", url=url, error=str(e))
                raise TikTokDownloadError(f"Headful retry failed: {str(e)}")

        # Should not reach here
        raise TikTokDownloadError("Failed to download video")