import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from platform_crawler.tiktok.tiktok_download_client import (
    TikTokDownloadClient,
    TikTokDownloadRequest,
    TikTokDownloadResponse,
    TikTokVideoInfo,
    TikTokDownloadError,
    TikTokInvalidUrlError,
    TikTokNavigationError,
    TikTokNoDownloadLinkError,
    TikTokDownloadFailedError,
    TikTokInvalidVideoError
)


class TestTikTokDownloadClient:
    """Test the TikTokDownloadClient functionality."""

    def test_client_initialization(self):
        """Test client initialization with custom parameters."""
        client = TikTokDownloadClient(host="test-host", port="9999", timeout=120)
        assert client.base_url == "http://test-host:9999"
        assert client.timeout == 120

    def test_client_initialization_defaults(self):
        """Test client initialization with default parameters."""
        client = TikTokDownloadClient()
        assert client.base_url == "http://localhost:5680"
        assert client.timeout == 180

    def test_parse_video_info(self):
        """Test parsing video info from API response."""
        client = TikTokDownloadClient()
        video_info_dict = {
            "id": "test123",
            "title": "Test Video",
            "author": "testuser",
            "duration": 45.5,
            "thumbnail_url": "http://example.com/thumb.jpg"
        }

        video_info = client._parse_video_info(video_info_dict)

        assert video_info.id == "test123"
        assert video_info.title == "Test Video"
        assert video_info.author == "testuser"
        assert video_info.duration == 45.5
        assert video_info.thumbnail_url == "http://example.com/thumb.jpg"

    def test_parse_video_info_no_thumbnail(self):
        """Test parsing video info without thumbnail."""
        client = TikTokDownloadClient()
        video_info_dict = {
            "id": "test123",
            "title": "Test Video",
            "author": "testuser",
            "duration": 45.5
        }

        video_info = client._parse_video_info(video_info_dict)

        assert video_info.id == "test123"
        assert video_info.title == "Test Video"
        assert video_info.author == "testuser"
        assert video_info.duration == 45.5
        assert video_info.thumbnail_url is None

    def test_parse_response_success(self):
        """Test parsing successful API response."""
        client = TikTokDownloadClient()
        response_data = {
            "status": "success",
            "message": "Video download URL resolved successfully",
            "download_url": "http://example.com/video.mp4",
            "video_info": {
                "id": "test123",
                "title": "Test Video",
                "author": "testuser",
                "duration": 45.5
            },
            "file_size": 1000000,
            "execution_time": 5.0
        }

        response = client._parse_response(response_data)

        assert response.status == "success"
        assert response.message == "Video download URL resolved successfully"
        assert response.download_url == "http://example.com/video.mp4"
        assert response.video_info.id == "test123"
        assert response.file_size == 1000000
        assert response.execution_time == 5.0

    def test_parse_response_error(self):
        """Test parsing error API response."""
        client = TikTokDownloadClient()
        response_data = {
            "status": "error",
            "message": "Failed to resolve download URL",
            "error_code": "NO_DOWNLOAD_LINK",
            "error_details": {
                "code": "NO_DOWNLOAD_LINK",
                "message": "Could not resolve download URL"
            },
            "execution_time": 3.0
        }

        response = client._parse_response(response_data)

        assert response.status == "error"
        assert response.message == "Failed to resolve download URL"
        assert response.download_url is None
        assert response.video_info is None
        assert response.error_code == "NO_DOWNLOAD_LINK"
        assert response.execution_time == 3.0

    def test_create_exception_invalid_url(self):
        """Test creating exception for INVALID_URL error."""
        client = TikTokDownloadClient()
        response = TikTokDownloadResponse(
            status="error",
            message="Invalid TikTok video URL format",
            error_code="INVALID_URL",
            execution_time=1.0
        )

        exception = client._create_exception(response)

        assert isinstance(exception, TikTokInvalidUrlError)
        assert str(exception) == "Invalid TikTok video URL format"
        assert exception.error_code == "INVALID_URL"
        assert exception.execution_time == 1.0

    def test_create_exception_navigation_failed(self):
        """Test creating exception for NAVIGATION_FAILED error."""
        client = TikTokDownloadClient()
        response = TikTokDownloadResponse(
            status="error",
            message="Browser navigation failed",
            error_code="NAVIGATION_FAILED",
            execution_time=10.0
        )

        exception = client._create_exception(response)

        assert isinstance(exception, TikTokNavigationError)
        assert str(exception) == "Browser navigation failed"
        assert exception.error_code == "NAVIGATION_FAILED"

    def test_create_exception_unknown(self):
        """Test creating exception for unknown error code."""
        client = TikTokDownloadClient()
        response = TikTokDownloadResponse(
            status="error",
            message="Unknown error occurred",
            error_code="UNKNOWN_ERROR",
            execution_time=2.0
        )

        exception = client._create_exception(response)

        assert isinstance(exception, TikTokDownloadError)
        assert str(exception) == "Unknown error occurred"
        assert exception.error_code == "UNKNOWN_ERROR"

    @pytest.mark.asyncio
    async def test_resolve_download_success(self):
        """Test successful download resolution."""
        client = TikTokDownloadClient()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Video download URL resolved successfully",
            "download_url": "http://example.com/video.mp4",
            "video_info": {
                "id": "test123",
                "title": "Test Video",
                "author": "testuser",
                "duration": 45.5
            },
            "execution_time": 5.0
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            response, should_retry = await client.resolve_download("https://tiktok.com/test", force_headful=False)

        assert response.status == "success"
        assert response.download_url == "http://example.com/video.mp4"
        assert should_retry is False

    @pytest.mark.asyncio
    async def test_resolve_download_error_with_retry(self):
        """Test download resolution error that should trigger retry."""
        client = TikTokDownloadClient()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "status": "error",
            "message": "Browser navigation failed",
            "error_code": "NAVIGATION_FAILED",
            "execution_time": 8.0
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            response, should_retry = await client.resolve_download("https://tiktok.com/test", force_headful=False)

        assert response.status == "error"
        assert response.error_code == "NAVIGATION_FAILED"
        assert should_retry is True

    @pytest.mark.asyncio
    async def test_resolve_download_error_no_retry(self):
        """Test download resolution error that should not trigger retry."""
        client = TikTokDownloadClient()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "status": "error",
            "message": "Invalid TikTok video URL format",
            "error_code": "INVALID_URL",
            "execution_time": 0.5
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(TikTokInvalidUrlError):
                await client.resolve_download("https://tiktok.com/test", force_headful=False)

    @pytest.mark.asyncio
    async def test_resolve_download_http_5xx_error(self):
        """Test download resolution with HTTP 5xx error."""
        client = TikTokDownloadClient()

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 500 Error")
        mock_response.status_code = 500

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            response, should_retry = await client.resolve_download("https://tiktok.com/test", force_headful=False)

        assert response.status == "error"
        assert response.error_code == "HTTP_ERROR"
        assert should_retry is True

    @pytest.mark.asyncio
    async def test_download_video_with_retry_success(self):
        """Test successful download with retry logic."""
        client = TikTokDownloadClient()

        # Mock successful resolve_download
        async def mock_resolve(url, force_headful=False):
            return TikTokDownloadResponse(
                status="success",
                message="Success",
                download_url="http://example.com/video.mp4",
                execution_time=5.0
            ), False

        client.resolve_download = mock_resolve

        response = await client.download_video_with_retry("https://tiktok.com/test")

        assert response.status == "success"
        assert response.download_url == "http://example.com/video.mp4"

    @pytest.mark.asyncio
    async def test_download_video_with_retry_headful_success(self):
        """Test download that fails headless but succeeds headful."""
        client = TikTokDownloadClient()
        call_count = 0

        async def mock_resolve(url, force_headful=False):
            nonlocal call_count
            call_count += 1
            if force_headful:
                return TikTokDownloadResponse(
                    status="success",
                    message="Success",
                    download_url="http://example.com/video.mp4",
                    execution_time=8.0
                ), False
            else:
                return TikTokDownloadResponse(
                    status="error",
                    message="Navigation failed",
                    error_code="NAVIGATION_FAILED",
                    execution_time=5.0
                ), True

        client.resolve_download = mock_resolve

        response = await client.download_video_with_retry("https://tiktok.com/test")

        assert response.status == "success"
        assert response.download_url == "http://example.com/video.mp4"
        assert call_count == 2  # Should be called twice: headless + headful

    @pytest.mark.asyncio
    async def test_download_video_with_retry_failure(self):
        """Test download that fails both headless and headful."""
        client = TikTokDownloadClient()

        async def mock_resolve(url, force_headful=False):
            return TikTokDownloadResponse(
                status="error",
                message="Invalid URL",
                error_code="INVALID_URL",
                execution_time=1.0
            ), False

        client.resolve_download = mock_resolve

        with pytest.raises(TikTokInvalidUrlError):
            await client.download_video_with_retry("https://tiktok.com/test")

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client as context manager."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            async with TikTokDownloadClient() as client:
                assert client.client == mock_client
                mock_client.aclose.assert_not_called()

            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Test manual client closing."""
        client = TikTokDownloadClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Initialize client by accessing property
            _ = client.client

            await client.close()
            mock_client.aclose.assert_called_once()
            assert client._client is None