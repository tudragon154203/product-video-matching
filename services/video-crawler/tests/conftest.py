"""
Pytest configuration and shared fixtures for video-crawler tests
"""
import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure common_py is in the path for tests
import sys
TESTS_DIR = Path(__file__).resolve().parent
SERVICE_ROOT = TESTS_DIR.parent
REPO_ROOT = SERVICE_ROOT.parent.parent
for candidate in (SERVICE_ROOT, REPO_ROOT, REPO_ROOT / "libs"):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)


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


@pytest.fixture
def tiktok_env_mock(temp_dir):
    """Mock TIKTOK_VIDEO_STORAGE_PATH environment variable for TikTok-related tests"""
    with patch.dict(os.environ, {'TIKTOK_VIDEO_STORAGE_PATH': temp_dir}):
        yield temp_dir


@pytest.fixture
def mock_db():
    """Mock database manager for testing."""
    from unittest.mock import AsyncMock
    from common_py.database import DatabaseManager

    db = AsyncMock(spec=DatabaseManager)

    # Setup default mock responses
    db.fetch_one.return_value = None
    db.fetch_all.return_value = []
    db.execute.return_value = None

    # Add mock pool for connection validation
    mock_pool = AsyncMock()
    db.pool = mock_pool

    return db


@pytest.fixture
def parallel_video_service(mock_db):
    """Parallel video service instance for testing."""
    from services.parallel_video_service import ParallelVideoService
    from services.streaming_pipeline import PipelineConfig

    config = PipelineConfig(
        max_concurrent_downloads=2,
        max_concurrent_processing=2,
        download_queue_size=10,
        processing_queue_size=10,
        batch_size_for_processing=5,
        search_result_buffer_size=5
    )

    return ParallelVideoService(mock_db, config=config)


@pytest.fixture
def platform_queries():
    """Sample platform queries for testing."""
    return {
        "youtube": ["ergonomic pillows review", "pillow unboxing"],
        "tiktok": ["#pillow", "#sleep", "#bedding"]
    }


@pytest.fixture
def sample_video_data():
    """Sample video data for testing."""
    return {
        "video_id": "test_video_123",
        "platform": "youtube",
        "url": "https://youtube.com/watch?v=test123",
        "title": "Test Video Title",
        "duration_s": 120,
        "published_at": "2025-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_video_data_list():
    """List of sample video data for testing."""
    return [
        {
            "video_id": f"video_{i}",
            "platform": "youtube" if i % 2 == 0 else "tiktok",
            "url": f"https://example.com/video_{i}",
            "title": f"Test Video {i}",
            "duration_s": 30 + (i * 10)
        }
        for i in range(5)
    ]


@pytest.fixture
def mock_event_emitter():
    """Mock event emitter for testing."""
    from unittest.mock import AsyncMock
    emitter = AsyncMock()
    emitter.publish_videos_keyframes_ready = AsyncMock()
    return emitter


@pytest.fixture
def mock_progress_manager():
    """Mock job progress manager for testing."""
    from unittest.mock import AsyncMock
    manager = AsyncMock()
    manager.update_job_progress = AsyncMock()
    return manager


@pytest.fixture
def video_processor(mock_db):
    """Video processor instance for testing."""
    from services.video_processor import VideoProcessor
    return VideoProcessor(mock_db)


@pytest.fixture
def streaming_pipeline(mock_db):
    """Streaming pipeline instance for testing."""
    from services.streaming_pipeline import StreamingVideoPipeline, PipelineConfig

    config = PipelineConfig(
        max_concurrent_downloads=2,
        max_concurrent_processing=2,
        download_queue_size=10,
        processing_queue_size=10,
        batch_size_for_processing=5,
        search_result_buffer_size=5
    )

    return StreamingVideoPipeline(mock_db, config)


@pytest.fixture
def sample_keyframes():
    """Sample keyframe data for testing."""
    return [
        (0.0, "/path/to/frame_0.jpg"),
        (5.0, "/path/to/frame_1.jpg"),
        (10.0, "/path/to/frame_2.jpg")
    ]


@pytest.fixture
def idempotency_manager(mock_db):
    """Idempotency manager instance for testing."""
    from services.idempotency_manager import IdempotencyManager
    return IdempotencyManager(mock_db)
