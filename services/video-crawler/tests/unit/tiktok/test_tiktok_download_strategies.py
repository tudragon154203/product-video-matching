import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
import httpx

from platform_crawler.tiktok.download_strategies.factory import TikTokDownloadStrategyFactory, TikTokDownloadStrategyRegistry
from platform_crawler.tiktok.download_strategies.base import TikTokAntiBotError
from platform_crawler.tiktok.download_strategies.scrapling_api_strategy import ScraplingApiDownloadStrategy
from platform_crawler.tiktok.download_strategies.tikwm_strategy import TikwmDownloadStrategy


class _AsyncBytesIterator:
    """Async iterator helper that yields provided chunks."""

    def __init__(self, chunks):
        self._iterator = iter(chunks)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._iterator)
        except StopIteration:
            raise StopAsyncIteration


class TestTikTokDownloadStrategyFactory:
    """Test the strategy factory functionality."""

    def test_create_default_scrapling_api_strategy(self):
        """Test that default strategy is scrapling-api."""
        config = {}
        strategy = TikTokDownloadStrategyFactory.create_strategy(config)
        assert isinstance(strategy, ScraplingApiDownloadStrategy)

    def test_create_explicit_tikwm_strategy(self):
        """Test creating tikwm strategy explicitly."""
        config = {"TIKTOK_DOWNLOAD_STRATEGY": "tikwm"}
        strategy = TikTokDownloadStrategyFactory.create_strategy(config)
        assert isinstance(strategy, TikwmDownloadStrategy)

    def test_create_scrapling_api_strategy(self):
        """Test creating scrapling-api strategy."""
        with patch.dict(os.environ, {}, clear=True):  # Clear all environment variables
            config = {"TIKTOK_DOWNLOAD_STRATEGY": "scrapling-api"}
            strategy = TikTokDownloadStrategyFactory.create_strategy(config)
            assert isinstance(strategy, ScraplingApiDownloadStrategy)

    def test_create_scrapling_api_strategy_underscore(self):
        """Test creating scrapling_api strategy with underscore."""
        with patch.dict(os.environ, {}, clear=True):  # Clear all environment variables
            config = {"TIKTOK_DOWNLOAD_STRATEGY": "scrapling_api"}
            strategy = TikTokDownloadStrategyFactory.create_strategy(config)
            assert isinstance(strategy, ScraplingApiDownloadStrategy)

    def test_create_tikwm_strategy(self):
        """Test creating tikwm strategy."""
        with patch.dict(os.environ, {}, clear=True):  # Clear all environment variables
            config = {"TIKTOK_DOWNLOAD_STRATEGY": "tikwm"}
            strategy = TikTokDownloadStrategyFactory.create_strategy(config)
            assert isinstance(strategy, TikwmDownloadStrategy)


    def test_create_strategy_from_env_var(self):
        """Test creating strategy from environment variable."""
        with patch.dict(os.environ, {"TIKTOK_DOWNLOAD_STRATEGY": "scrapling-api"}):
            config = {}
            strategy = TikTokDownloadStrategyFactory.create_strategy(config)
            assert isinstance(strategy, ScraplingApiDownloadStrategy)

    def test_invalid_strategy_raises_error(self):
        """Test that invalid strategy raises ValueError."""
        with patch.dict(os.environ, {"TIKTOK_DOWNLOAD_STRATEGY": ""}, clear=True):
            config = {"TIKTOK_DOWNLOAD_STRATEGY": "invalid-strategy"}
            with pytest.raises(ValueError, match="Unknown TikTok download strategy: invalid-strategy"):
                TikTokDownloadStrategyFactory.create_strategy(config)


class TestTikTokDownloadStrategyRegistry:
    """Test the strategy registry functionality."""

    def test_list_strategies(self):
        """Test listing available strategies."""
        strategies = TikTokDownloadStrategyRegistry.list_strategies()
        assert "scrapling_api" in strategies
        assert "tikwm" in strategies

    def test_register_new_strategy(self):
        """Test registering a new strategy."""
        class MockStrategy:
            def __init__(self, config):
                pass

        TikTokDownloadStrategyRegistry.register_strategy("mock", MockStrategy)
        strategies = TikTokDownloadStrategyRegistry.list_strategies()
        assert "mock" in strategies

        # Test creating the registered strategy
        strategy = TikTokDownloadStrategyRegistry.create_strategy("mock", {})
        assert isinstance(strategy, MockStrategy)

    def test_create_unregistered_strategy_raises_error(self):
        """Test that creating unregistered strategy raises error."""
        with pytest.raises(ValueError, match="Unknown TikTok download strategy: nonexistent"):
            TikTokDownloadStrategyRegistry.create_strategy("nonexistent", {})


class TestScraplingApiDownloadStrategy:
    """Test the scrapling-api strategy implementation."""

    def test_strategy_initialization(self):
        """Test ScraplingApiDownloadStrategy initialization."""
        config = {
            "retries": 5,
            "timeout": 60,
            "TIKTOK_CRAWL_HOST": "test-host",
            "TIKTOK_CRAWL_HOST_PORT": "9999",
            "TIKTOK_DOWNLOAD_TIMEOUT": 120
        }
        strategy = ScraplingApiDownloadStrategy(config)
        assert strategy.retries == 5
        assert strategy.timeout == 60
        assert strategy.api_host == "test-host"
        assert strategy.api_port == "9999"
        assert strategy.api_timeout == 120

    def test_strategy_initialization_defaults(self):
        """Test ScraplingApiDownloadStrategy initialization with defaults."""
        strategy = ScraplingApiDownloadStrategy({})
        assert strategy.api_host == "localhost"
        assert strategy.api_port == "5680"
        assert strategy.api_timeout == 180
        assert strategy.max_file_size == 500 * 1024 * 1024

    @patch('platform_crawler.tiktok.tiktok_download_client.TikTokDownloadClient')
    @patch('platform_crawler.tiktok.download_strategies.scrapling_api_strategy.record_download_metrics')
    def test_download_video_success(self, mock_metrics, mock_client_class):
        """Test successful video download."""
        # Mock the client and its response
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock successful API response
        mock_api_response = MagicMock()
        mock_api_response.download_url = "http://example.com/video.mp4"
        mock_api_response.execution_time = 5.0
        mock_client.download_video_with_retry.return_value = mock_api_response

        with patch.object(ScraplingApiDownloadStrategy, '_stream_video_file', new_callable=AsyncMock) as mock_stream, \
                patch('os.path.exists', return_value=True), \
                patch('os.path.getsize', return_value=1000000):  # 1MB file

            mock_stream.return_value = True

            strategy = ScraplingApiDownloadStrategy({"retries": 1, "timeout": 30})
            result = strategy.download_video("https://tiktok.com/test", "test_id", "/tmp")

        assert result is not None
        assert result.endswith("test_id.mp4")
        mock_metrics.assert_called_once()

    @patch('platform_crawler.tiktok.tiktok_download_client.TikTokDownloadClient')
    @patch('platform_crawler.tiktok.download_strategies.scrapling_api_strategy.record_download_metrics')
    def test_download_video_api_error(self, mock_metrics, mock_client_class):
        """Test download with API error."""
        # Mock the client
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock API error response
        mock_api_response = MagicMock()
        mock_api_response.download_url = None
        mock_api_response.error_code = "NO_DOWNLOAD_LINK"
        mock_client.download_video_with_retry.return_value = mock_api_response

        strategy = ScraplingApiDownloadStrategy({"retries": 1, "timeout": 30})
        result = strategy.download_video("https://tiktok.com/test", "test_id", "/tmp")

        assert result is None
        mock_metrics.assert_called_once()

    @patch('platform_crawler.tiktok.tiktok_download_client.TikTokDownloadClient')
    @patch('platform_crawler.tiktok.download_strategies.scrapling_api_strategy.record_download_metrics')
    def test_download_video_file_too_large(self, mock_metrics, mock_client_class):
        """Test download when file is too large."""
        # Mock the client and its response
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock successful API response
        mock_api_response = MagicMock()
        mock_api_response.download_url = "http://example.com/video.mp4"
        mock_api_response.execution_time = 5.0
        mock_client.download_video_with_retry.return_value = mock_api_response

        # Mock file exists but is too large (>500MB)
        with patch.object(ScraplingApiDownloadStrategy, '_stream_video_file', new_callable=AsyncMock) as mock_stream, \
                patch('os.path.exists', return_value=True), \
                patch('os.path.getsize', return_value=600 * 1024 * 1024), \
                patch('os.remove'):

            mock_stream.return_value = True

            strategy = ScraplingApiDownloadStrategy({"retries": 1, "timeout": 30})
            result = strategy.download_video("https://tiktok.com/test", "test_id", "/tmp")

        assert result is None
        mock_metrics.assert_called_once()

    async def test_extract_keyframes_method_exists(self):
        """Test that extract_keyframes method exists and is callable."""
        strategy = ScraplingApiDownloadStrategy({"keyframe_storage_path": "/tmp"})
        assert hasattr(strategy, 'extract_keyframes')
        assert callable(strategy.extract_keyframes)


class TestTikwmDownloadStrategy:
    """Test the TikWM strategy implementation."""

    def test_strategy_initialization(self):
        """Test TikwmDownloadStrategy initialization."""
        config = {"retries": 5, "timeout": 60}
        strategy = TikwmDownloadStrategy(config)
        assert strategy.retries == 5
        assert strategy.timeout == 60
        assert strategy.config == config
        assert strategy.tikwm_base_url == "https://www.tikwm.com/video/media/play"
        assert strategy.max_file_size == 500 * 1024 * 1024
        assert strategy.max_retries == 2
        assert strategy.retry_delay == 1

    def test_strategy_initialization_defaults(self):
        """Test TikwmDownloadStrategy initialization with defaults."""
        strategy = TikwmDownloadStrategy({})
        assert strategy.download_timeout == 30
        assert strategy.max_file_size == 500 * 1024 * 1024
        assert strategy.max_retries == 2
        assert strategy.retry_delay == 1

    def test_extract_video_id_from_url_success(self):
        """Test successful video ID extraction from TikTok URL."""
        strategy = TikwmDownloadStrategy({})
        url = "https://www.tiktok.com/@username/video/1234567890123456789"
        video_id = strategy._extract_video_id_from_url(url)
        assert video_id == "1234567890123456789"

    def test_extract_video_id_from_url_failure(self):
        """Test video ID extraction failure for invalid URL."""
        strategy = TikwmDownloadStrategy({})
        url = "https://example.com/not-tiktok"
        video_id = strategy._extract_video_id_from_url(url)
        assert video_id is None

    @patch('platform_crawler.tiktok.download_strategies.tikwm_strategy.record_download_metrics')
    def test_download_video_success(self, mock_metrics):
        """Test successful video download."""
        # Mock the async helper method
        with patch.object(TikwmDownloadStrategy, '_download_video_async_with_retries',
                          new_callable=AsyncMock) as mock_async_helper:
            mock_async_helper.return_value = ("/tmp/test_id.mp4", 0)  # (result, retries)

            with patch('os.path.exists', return_value=True), \
                    patch('os.path.getsize', return_value=1000000):  # 1MB file
                strategy = TikwmDownloadStrategy({"retries": 1, "timeout": 30})
                result = strategy.download_video("https://tiktok.com/test", "test_id", "/tmp")

        assert result == "/tmp/test_id.mp4"
        mock_metrics.assert_called_once()
        call_args = mock_metrics.call_args[1]
        assert call_args['strategy'] == 'tikwm'
        assert call_args['video_id'] == 'test_id'
        assert call_args['success'] is True
        assert call_args['file_size'] == 1000000

    @patch('platform_crawler.tiktok.download_strategies.tikwm_strategy.record_download_metrics')
    def test_download_video_no_video_id(self, mock_metrics):
        """Test download with invalid URL (no video ID)."""
        with patch.object(TikwmDownloadStrategy, '_download_video_async_with_retries',
                          new_callable=AsyncMock) as mock_async_helper:
            # Simulate video ID extraction failure
            error = ValueError("Could not extract video ID from TikTok URL")
            error.error_code = "NO_VIDEO_ID"
            mock_async_helper.side_effect = error

            strategy = TikwmDownloadStrategy({"retries": 1, "timeout": 30})

            with pytest.raises(ValueError) as exc_info:
                strategy.download_video("https://example.com/invalid", "test_id", "/tmp")

            assert exc_info.value.error_code == "NO_VIDEO_ID"

        mock_metrics.assert_called_once()
        call_args = mock_metrics.call_args[1]
        assert call_args['strategy'] == 'tikwm'
        assert call_args['success'] is False
        assert call_args['error_code'] == 'NO_VIDEO_ID'

    @patch('platform_crawler.tiktok.download_strategies.tikwm_strategy.record_download_metrics')
    def test_download_video_file_too_large(self, mock_metrics):
        """Test download when file is too large."""
        with patch.object(TikwmDownloadStrategy, '_download_video_async_with_retries',
                          new_callable=AsyncMock) as mock_async_helper:
            # Simulate file too large error
            error = ValueError("Downloaded file exceeds size limit")
            error.error_code = "SIZE_LIMIT_EXCEEDED"
            mock_async_helper.side_effect = error

            strategy = TikwmDownloadStrategy({"retries": 1, "timeout": 30})

            with pytest.raises(ValueError) as exc_info:
                strategy.download_video("https://tiktok.com/test", "test_id", "/tmp")

            assert exc_info.value.error_code == "SIZE_LIMIT_EXCEEDED"

        mock_metrics.assert_called_once()
        call_args = mock_metrics.call_args[1]
        assert call_args['strategy'] == 'tikwm'
        assert call_args['success'] is False
        assert call_args['error_code'] == 'SIZE_LIMIT_EXCEEDED'

    async def test_resolve_url_with_head_success(self):
        """Test successful HEAD request to resolve URL."""
        strategy = TikwmDownloadStrategy({"timeout": 30})

        with patch('platform_crawler.tiktok.download_strategies.tikwm_strategy.httpx.AsyncClient') as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.url = "https://final-url.com/video.mp4"
            mock_response.headers = {
                "content-type": "video/mp4",
                "content-length": "1000000"
            }

            # Make head method async
            mock_session = MagicMock()
            mock_session.head = AsyncMock(return_value=mock_response)
            mock_httpx.return_value.__aenter__.return_value = mock_session

            final_url = await strategy._resolve_url_with_head("https://tikwm.com/video.mp4", "test_id")

            assert final_url == "https://final-url.com/video.mp4"

    async def test_resolve_url_with_head_invalid_content_type(self):
        """Test HEAD request with non-video content type."""
        strategy = TikwmDownloadStrategy({"timeout": 30})

        with patch('platform_crawler.tiktok.download_strategies.tikwm_strategy.httpx.AsyncClient') as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/html"}

            # Make head method async
            mock_session = MagicMock()
            mock_session.head = AsyncMock(return_value=mock_response)
            mock_httpx.return_value.__aenter__.return_value = mock_session

            with pytest.raises(ValueError) as exc_info:
                await strategy._resolve_url_with_head("https://tikwm.com/video.mp4", "test_id")

            assert exc_info.value.error_code == "INVALID_CONTENT_TYPE"

    async def test_stream_video_file_success(self):
        """Test successful video file streaming."""
        strategy = TikwmDownloadStrategy({"timeout": 30})

        mock_response = MagicMock()
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_bytes.return_value = _AsyncBytesIterator([b'fake_video_data'])

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream.return_value = mock_stream_ctx
        mock_client.stream.assert_not_called()

        mock_client_ctx = MagicMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch('platform_crawler.tiktok.download_strategies.tikwm_strategy.httpx.AsyncClient', return_value=mock_client_ctx), \
                patch('builtins.open', mock_open()) as mocked_open, \
                patch('os.path.getsize', return_value=1000000):  # 1MB file

            success = await strategy._stream_video_file(
                "http://example.com/video.mp4",
                "/tmp/test.mp4",
                "test_id"
            )

        assert success is True
        mocked_open.assert_called_once_with("/tmp/test.mp4", "wb")
        mock_client.stream.assert_called_once_with("GET", "http://example.com/video.mp4")

    async def test_stream_video_file_size_exceeded(self):
        """Test video file streaming with size exceeded."""
        strategy = TikwmDownloadStrategy({"timeout": 30})

        # Reduce size limit to keep test lightweight
        strategy.max_file_size = 1024  # 1KB

        oversized_chunk = b'a' * 2048

        mock_response = MagicMock()
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_bytes.return_value = _AsyncBytesIterator([oversized_chunk])

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream.return_value = mock_stream_ctx
        mock_client_ctx = MagicMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch('platform_crawler.tiktok.download_strategies.tikwm_strategy.httpx.AsyncClient', return_value=mock_client_ctx), \
                patch('builtins.open', mock_open()) as mocked_open, \
                patch('os.remove') as mock_remove:

            with pytest.raises(ValueError) as exc_info:
                await strategy._stream_video_file(
                    "http://example.com/video.mp4",
                    "/tmp/test.mp4",
                    "test_id"
                )

        assert exc_info.value.error_code == "SIZE_LIMIT_EXCEEDED"
        mocked_open.assert_called_once_with("/tmp/test.mp4", "wb")
        mock_remove.assert_called_once_with("/tmp/test.mp4")

    async def test_extract_keyframes_method_exists(self):
        """Test that extract_keyframes method exists and is callable."""
        strategy = TikwmDownloadStrategy({"keyframe_storage_path": "/tmp"})
        assert hasattr(strategy, 'extract_keyframes')
        assert callable(strategy.extract_keyframes)

    def test_is_retryable_error(self):
        """Test retryable error detection."""
        strategy = TikwmDownloadStrategy({})

        # Test HTTP 5xx errors (retryable)
        error_5xx = httpx.HTTPStatusError("Server Error", request=MagicMock(), response=MagicMock(status_code=500))
        assert strategy._is_retryable_error(error_5xx) is True

        # Test HTTP 4xx errors (not retryable)
        error_4xx = httpx.HTTPStatusError("Client Error", request=MagicMock(), response=MagicMock(status_code=404))
        assert strategy._is_retryable_error(error_4xx) is False

        # Test network errors (retryable)
        error_connect = httpx.ConnectError("Connection failed")
        assert strategy._is_retryable_error(error_connect) is True

        error_timeout = httpx.TimeoutException("Timeout")
        assert strategy._is_retryable_error(error_timeout) is True

        # Test other errors (not retryable)
        error_generic = ValueError("Generic error")
        assert strategy._is_retryable_error(error_generic) is False
