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
            "url": "https://youtube.com/watch?v=test_video_1",
            "title": "Test Video 1",
            "duration_s": 30,
            "platform": "youtube",
            "author": "test_user1",
            "view_count": 1000,
            "create_time": current_time - 3600  # 1 hour ago
        },
        {
            "video_id": "test_video_2",
            "url": "https://youtube.com/watch?v=test_video_2",
            "title": "Test Video 2",
            "duration_s": 45,
            "platform": "youtube",
            "author": "test_user2",
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
    config.NUM_PARALLEL_DOWNLOADS = 3
    return config