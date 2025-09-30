import asyncio
import os
from platform_crawler.tiktok.tiktok_downloader import TikTokDownloader


def test_keyframe_extraction():
    """Test TikTok keyframe extraction integration"""
    downloader = TikTokDownloader({})
    # The method is async, so we need to await it
    result = asyncio.run(downloader.extract_keyframes("video_path", "video_id"))
    # Should return a directory path even if no keyframes are extracted due to missing file
    assert result is not None
    # The directory should still be created even if extraction fails
    assert os.path.exists(result)
