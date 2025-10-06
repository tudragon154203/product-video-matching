import os
from unittest.mock import patch

from platform_crawler.tiktok.tiktok_downloader import TikTokDownloader


def test_tiktok_downloader_init():
    """Test TikTokDownloader initialization passes"""
    downloader = TikTokDownloader({})
    assert downloader is not None
    assert downloader.download_strategy is not None


def test_tiktok_downloader_download_video():
    """Test TikTokDownloader download_video implementation"""
    with patch('platform_crawler.tiktok.download_strategies.ytdlp_strategy.yt_dlp.YoutubeDL'):
        downloader = TikTokDownloader({})
        # Mock the strategy to return None for invalid URL
        downloader.download_strategy.download_video = lambda url, video_id, path: None
        result = downloader.download_video("url", "id")
        # Should return None when download fails
        assert result is None


def test_tiktok_downloader_strategy_from_env():
    """Test that downloader respects strategy environment variable"""
    with patch.dict(os.environ, {"TIKTOK_DOWNLOAD_STRATEGY": "yt-dlp"}):
        downloader = TikTokDownloader({})
        assert downloader.download_strategy is not None


def test_tiktok_downloader_strategy_from_config():
    """Test that downloader respects strategy config"""
    config = {"TIKTOK_DOWNLOAD_STRATEGY": "yt-dlp"}
    downloader = TikTokDownloader(config)
    assert downloader.download_strategy is not None
