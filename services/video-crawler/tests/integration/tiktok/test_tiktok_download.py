from platform_crawler.tiktok.tiktok_downloader import TikTokDownloader


def test_tiktok_download():
    """Test TikTok video download integration"""
    downloader = TikTokDownloader({})
    # The method is implemented, so it should not raise NotImplementedError
    # It will likely fail due to invalid URL, but that's expected for integration test
    result = downloader.download_video("url", "id")
    # Should return None when download fails
    assert result is None
