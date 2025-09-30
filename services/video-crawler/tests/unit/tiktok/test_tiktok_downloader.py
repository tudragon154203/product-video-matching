from platform_crawler.tiktok.tiktok_downloader import TikTokDownloader


def test_tiktok_downloader_init():
    """Test TikTokDownloader initialization passes"""
    downloader = TikTokDownloader({})
    assert downloader is not None


def test_tiktok_downloader_download_video():
    """Test TikTokDownloader download_video implementation"""
    downloader = TikTokDownloader({})
    # The method is implemented, so it should not raise NotImplementedError
    # It will likely fail due to invalid URL, but that's expected
    result = downloader.download_video("url", "id")
    # Should return None when download fails
    assert result is None
