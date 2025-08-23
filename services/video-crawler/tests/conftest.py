"""
Pytest configuration and shared fixtures for video-crawler tests
"""
import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Ensure common_py is in the path for tests
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def mock_video_data():
    """Mock video data for testing"""
    import time
    current_time = time.time()
    
    return [
        {
            "video_id": "test_video_1",
            "url": "https://tiktok.com/@user1/video/test_video_1",
            "title": "Test Video 1",
            "duration_s": 30,
            "platform": "tiktok",
            "author": "test_user1",
            "view_count": 1000,
            "create_time": current_time - 3600  # 1 hour ago
        },
        {
            "video_id": "test_video_2", 
            "url": "https://tiktok.com/@user2/video/test_video_2",
            "title": "Test Video 2 Vietnam",
            "duration_s": 45,
            "platform": "tiktok", 
            "author": "vietnam_user",
            "view_count": 2000,
            "create_time": current_time - 7200  # 2 hours ago
        }
    ]

@pytest.fixture
def mock_downloaded_video_data(mock_video_data, temp_dir):
    """Mock downloaded video data with local paths"""
    downloaded = []
    for i, video in enumerate(mock_video_data):
        video_copy = video.copy()
        video_copy["local_path"] = str(Path(temp_dir) / f"video_{i+1}.mp4")
        downloaded.append(video_copy)
    return downloaded

@pytest.fixture
def mock_tiktok_api():
    """Mock TikTok API for testing"""
    mock_api = MagicMock()
    mock_api.create_sessions = AsyncMock()
    mock_api.close = AsyncMock()
    mock_api.hashtag = MagicMock()
    mock_api.trending = MagicMock()
    mock_api.video = MagicMock()
    return mock_api

@pytest.fixture
def mock_video_object():
    """Mock TikTok video object"""
    mock_video = MagicMock()
    mock_video.id = "test_video_123"
    mock_video.desc = "Test video description"
    mock_video.author.username = "test_user"
    mock_video.author.nickname = "Test User"
    mock_video.duration = 30
    mock_video.stats.playCount = 1000
    mock_video.stats.diggCount = 100
    mock_video.stats.shareCount = 10
    mock_video.stats.commentCount = 50
    mock_video.createTime = 1234567890
    return mock_video

@pytest.fixture
def vietnamese_test_videos():
    """Test videos with Vietnamese content"""
    return [
        {
            "title": "Review điện thoại mới ở Việt Nam",
            "author": "tech_vietnam",
            "view_count": 50000,
            "video_id": "vn_video_1"
        },
        {
            "title": "English tech review",
            "author": "tech_global", 
            "view_count": 30000,
            "video_id": "global_video_1"
        },
        {
            "title": "Sản phẩm công nghệ tại Sài Gòn",
            "author": "saigon_tech",
            "view_count": 75000,
            "video_id": "vn_video_2"
        }
    ]

@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    config = MagicMock()
    config.TIKTOK_MS_TOKEN = "test_token"
    config.TIKTOK_BROWSER = "chromium"
    config.TIKTOK_HEADLESS = True
    config.TIKTOK_PROXY_URL = ""
    config.TIKTOK_MAX_RETRIES = 3
    config.TIKTOK_SLEEP_AFTER = 2
    config.TIKTOK_SESSION_COUNT = 1
    config.TIKTOK_VIETNAM_REGION = True
    config.NUM_PARALLEL_DOWNLOADS = 3
    return config