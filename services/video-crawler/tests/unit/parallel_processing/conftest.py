"""
Shared fixtures and utilities for parallel processing tests.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any, List

from common_py.database import DatabaseManager
from services.idempotency_manager import IdempotencyManager
from services.streaming_pipeline import StreamingVideoPipeline, PipelineConfig, VideoTask
from services.parallel_video_service import ParallelVideoService
from services.video_processor import VideoProcessor


@pytest.fixture
def mock_db():
    """Mock database manager for testing."""
    db = AsyncMock(spec=DatabaseManager)

    # Setup default mock responses
    db.fetch_one.return_value = None
    db.fetch_all.return_value = []
    db.execute.return_value = None

    return db


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
def pipeline_config():
    """Test configuration for streaming pipeline."""
    return PipelineConfig(
        max_concurrent_downloads=2,
        max_concurrent_processing=2,
        download_queue_size=10,
        processing_queue_size=10,
        batch_size_for_processing=3,
        search_result_buffer_size=5
    )


@pytest.fixture
def platform_queries():
    """Sample platform queries for testing."""
    return {
        "youtube": ["ergonomic pillows review", "pillow unboxing"],
        "tiktok": ["#pillow", "#sleep", "#bedding"]
    }


@pytest.fixture
def idempotency_manager(mock_db):
    """Idempotency manager instance for testing."""
    return IdempotencyManager(mock_db)


@pytest.fixture
def streaming_pipeline(mock_db, pipeline_config):
    """Streaming pipeline instance for testing."""
    return StreamingVideoPipeline(mock_db, pipeline_config)


@pytest.fixture
def parallel_video_service(mock_db, pipeline_config):
    """Parallel video service instance for testing."""
    return ParallelVideoService(mock_db, config=pipeline_config)


@pytest.fixture
def video_processor(mock_db):
    """Video processor instance for testing."""
    return VideoProcessor(mock_db)


@pytest.fixture
def mock_event_emitter():
    """Mock event emitter for testing."""
    emitter = AsyncMock()
    emitter.publish_videos_keyframes_ready = AsyncMock()
    return emitter


@pytest.fixture
def mock_progress_manager():
    """Mock job progress manager for testing."""
    manager = AsyncMock()
    manager.update_job_progress = AsyncMock()
    return manager


@pytest.fixture
def temp_video_file(tmp_path):
    """Create a temporary video file for testing."""
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"fake video content")
    return str(video_file)


@pytest.fixture
def sample_keyframes():
    """Sample keyframe data for testing."""
    return [
        (0.0, "/path/to/frame_0.jpg"),
        (5.0, "/path/to/frame_1.jpg"),
        (10.0, "/path/to/frame_2.jpg")
    ]


class AsyncContextManager:
    """Helper for async context managers in tests."""

    def __init__(self, return_value=None):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_semaphore():
    """Mock semaphore for testing."""
    semaphore = AsyncMock()
    semaphore.__aenter__ = AsyncMock()
    semaphore.__aexit__ = AsyncMock()
    return semaphore


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def create_video_task(video_data: Dict[str, Any], job_id: str = "test_job") -> VideoTask:
    """Create a VideoTask instance for testing."""
    return VideoTask(
        video_data=video_data,
        job_id=job_id,
        platform=video_data["platform"],
        priority=1
    )


def assert_called_with_kwargs(mock_call, expected_kwargs: Dict[str, Any]):
    """Assert that a mock was called with specific keyword arguments."""
    actual_kwargs = mock_call.call_args[1] if mock_call.call_args else {}
    for key, value in expected_kwargs.items():
        assert actual_kwargs.get(key) == value, f"Expected {key}={value}, got {actual_kwargs.get(key)}"


async def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1):
    """Wait for a condition to become true or timeout."""
    start_time = asyncio.get_event_loop().time()

    while asyncio.get_event_loop().time() - start_time < timeout:
        if condition_func():
            return True
        await asyncio.sleep(interval)

    return False
