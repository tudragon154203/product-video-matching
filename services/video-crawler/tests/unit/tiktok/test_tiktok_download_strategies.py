import os
import pytest
from unittest.mock import patch, MagicMock

from platform_crawler.tiktok.download_strategies import (
    TikTokDownloadStrategyFactory,
    TikTokDownloadStrategyRegistry,
    YtdlpDownloadStrategy,
    TikTokAntiBotError
)


class TestTikTokDownloadStrategyFactory:
    """Test the strategy factory functionality."""

    def test_create_default_ytdlp_strategy(self):
        """Test that default strategy is yt-dlp."""
        config = {}
        strategy = TikTokDownloadStrategyFactory.create_strategy(config)
        assert isinstance(strategy, YtdlpDownloadStrategy)

    def test_create_explicit_ytdlp_strategy(self):
        """Test creating yt-dlp strategy explicitly."""
        config = {"TIKTOK_DOWNLOAD_STRATEGY": "yt-dlp"}
        strategy = TikTokDownloadStrategyFactory.create_strategy(config)
        assert isinstance(strategy, YtdlpDownloadStrategy)

    def test_create_strategy_from_env_var(self):
        """Test creating strategy from environment variable."""
        with patch.dict(os.environ, {"TIKTOK_DOWNLOAD_STRATEGY": "yt-dlp"}):
            config = {}
            strategy = TikTokDownloadStrategyFactory.create_strategy(config)
            assert isinstance(strategy, YtdlpDownloadStrategy)

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
        assert "yt-dlp" in strategies

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


class TestYtdlpDownloadStrategy:
    """Test the yt-dlp strategy implementation."""

    def test_strategy_initialization(self):
        """Test YtdlpDownloadStrategy initialization."""
        config = {"retries": 5, "timeout": 60}
        strategy = YtdlpDownloadStrategy(config)
        assert strategy.retries == 5
        assert strategy.timeout == 60
        assert strategy.config == config

    @patch('platform_crawler.tiktok.download_strategies.ytdlp_strategy.yt_dlp.YoutubeDL')
    def test_download_video_success(self, mock_youtubedl):
        """Test successful video download."""
        # Mock the YoutubeDL context manager
        mock_ydl_instance = MagicMock()
        mock_youtubedl.return_value.__enter__.return_value = mock_ydl_instance

        # Mock successful download
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1000000):  # 1MB file
            strategy = YtdlpDownloadStrategy({"retries": 1, "timeout": 30})
            result = strategy.download_video("https://tiktok.com/test", "test_id", "/tmp")

        assert result is not None
        assert result.endswith("test_id.mp4")

    @patch('platform_crawler.tiktok.download_strategies.ytdlp_strategy.yt_dlp.YoutubeDL')
    def test_download_video_file_too_large(self, mock_youtubedl):
        """Test download when file is too large."""
        mock_ydl_instance = MagicMock()
        mock_youtubedl.return_value.__enter__.return_value = mock_ydl_instance

        # Mock file exists but is too large (>500MB)
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=600 * 1024 * 1024), \
             patch('os.remove'):
            strategy = YtdlpDownloadStrategy({"retries": 1, "timeout": 30})
            result = strategy.download_video("https://tiktok.com/test", "test_id", "/tmp")

        assert result is None

    @patch('platform_crawler.tiktok.download_strategies.ytdlp_strategy.yt_dlp.YoutubeDL')
    def test_download_video_anti_bot_error(self, mock_youtubedl):
        """Test download with anti-bot error."""
        from yt_dlp.utils import DownloadError

        mock_ydl_instance = MagicMock()
        mock_youtubedl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.download.side_effect = DownloadError("HTTP Error 403: Forbidden")

        strategy = YtdlpDownloadStrategy({"retries": 1, "timeout": 30})

        with pytest.raises(TikTokAntiBotError):
            strategy.download_video("https://tiktok.com/test", "test_id", "/tmp")

    async def test_extract_keyframes_method_exists(self):
        """Test that extract_keyframes method exists and is callable."""
        strategy = YtdlpDownloadStrategy({"keyframe_storage_path": "/tmp"})
        assert hasattr(strategy, 'extract_keyframes')
        assert callable(strategy.extract_keyframes)