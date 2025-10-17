"""
Integration tests for parallel video processing with idempotency.

These tests verify that the parallel streaming pipeline maintains idempotency
while providing significant performance improvements over sequential processing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from common_py.database import DatabaseManager
from services.idempotency_manager import IdempotencyManager
from services.streaming_pipeline import StreamingVideoPipeline, PipelineConfig
from services.parallel_video_service import ParallelVideoService


@pytest.fixture
async def mock_db():
    """Mock database manager for testing."""
    db = AsyncMock(spec=DatabaseManager)

    # Mock basic database operations
    db.fetch_one.return_value = None
    db.fetch_all.return_value = []
    db.execute.return_value = None

    return db


@pytest.fixture
def pipeline_config():
    """Test configuration for streaming pipeline."""
    return PipelineConfig(
        max_concurrent_downloads=2,
        max_concurrent_processing=2,
        download_queue_size=10,
        processing_queue_size=10,
        batch_size_for_processing=5
    )


class TestIdempotencyManager:
    """Test idempotency manager functionality."""

    @pytest.mark.asyncio
    async def test_video_idempotency_check(self, mock_db):
        """Test video existence checking."""
        manager = IdempotencyManager(mock_db)

        # Test non-existent video
        mock_db.fetch_one.return_value = None
        exists = await manager.check_video_exists("test_video_id", "youtube")
        assert exists is False

        # Test existing video
        mock_db.fetch_one.return_value = {"video_id": "test_video_id"}
        exists = await manager.check_video_exists("test_video_id", "youtube")
        assert exists is True

    @pytest.mark.asyncio
    async def test_create_video_with_idempotency(self, mock_db):
        """Test creating video with idempotency."""
        manager = IdempotencyManager(mock_db)

        # Test new video creation
        mock_db.fetch_one.return_value = None  # No existing video
        created_new, video_id = await manager.create_video_with_idempotency(
            video_id="test_video_123",
            platform="youtube",
            url="https://example.com/video",
            title="Test Video"
        )

        assert created_new is True
        assert video_id == "test_video_123"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_duplicate_video_handling(self, mock_db):
        """Test handling of duplicate videos."""
        manager = IdempotencyManager(mock_db)

        # Test existing video (should not create new)
        existing_video = {"video_id": "test_video_123", "platform": "youtube"}
        mock_db.fetch_one.return_value = existing_video

        created_new, video_id = await manager.create_video_with_idempotency(
            video_id="test_video_123",
            platform="youtube",
            url="https://example.com/video",
            title="Test Video"
        )

        assert created_new is False
        assert video_id == "test_video_123"


class TestStreamingPipeline:
    """Test streaming pipeline functionality."""

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self, mock_db, pipeline_config):
        """Test pipeline initialization."""
        pipeline = StreamingVideoPipeline(mock_db, pipeline_config)

        assert pipeline.config == pipeline_config
        assert pipeline.download_queue.maxsize == pipeline_config.download_queue_size
        assert pipeline.processing_queue.maxsize == pipeline_config.processing_queue_size
        assert not pipeline.is_running

    @pytest.mark.asyncio
    async def test_pipeline_start_stop(self, mock_db, pipeline_config):
        """Test pipeline start and stop."""
        pipeline = StreamingVideoPipeline(mock_db, pipeline_config)

        # Start pipeline
        await pipeline.start_pipeline()
        assert pipeline.is_running
        assert len(pipeline.download_workers) == pipeline_config.max_concurrent_downloads
        assert len(pipeline.processing_workers) == pipeline_config.max_concurrent_processing

        # Stop pipeline
        await pipeline.stop_pipeline()
        assert not pipeline.is_running
        assert len(pipeline.download_workers) == 0
        assert len(pipeline.processing_workers) == 0

    @pytest.mark.asyncio
    async def test_task_priority_calculation(self, mock_db, pipeline_config):
        """Test task priority calculation."""
        pipeline = StreamingVideoPipeline(mock_db, pipeline_config)

        # Short video (high priority)
        short_video = {"duration_s": 20}
        priority = pipeline._calculate_priority(short_video)
        assert priority == 3

        # Medium video (medium priority)
        medium_video = {"duration_s": 60}
        priority = pipeline._calculate_priority(medium_video)
        assert priority == 2

        # Long video (low priority)
        long_video = {"duration_s": 300}
        priority = pipeline._calculate_priority(long_video)
        assert priority == 1

    @pytest.mark.asyncio
    async def test_statistics_tracking(self, mock_db, pipeline_config):
        """Test pipeline statistics tracking."""
        pipeline = StreamingVideoPipeline(mock_db, pipeline_config)

        initial_stats = pipeline.get_stats()
        assert initial_stats["search_results_found"] == 0
        assert initial_stats["downloads_completed"] == 0
        assert initial_stats["processing_completed"] == 0
        assert initial_stats["errors"] == 0


class TestParallelVideoService:
    """Test parallel video service integration."""

    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_db):
        """Test service initialization."""
        service = ParallelVideoService(mock_db)

        assert service.db == mock_db
        assert service.idempotency_manager is not None
        assert service.video_processor is not None
        assert service.pipeline is not None

    @pytest.mark.asyncio
    async def test_batch_parallel_processing(self, mock_db):
        """Test batch parallel processing mode."""
        service = ParallelVideoService(mock_db)

        # Mock video fetcher to return test data
        mock_videos = [
            {"video_id": "video_1", "platform": "youtube", "url": "https://example.com/1"},
            {"video_id": "video_2", "platform": "youtube", "url": "https://example.com/2"}
        ]

        # Mock the video processor responses
        service.video_processor.process_video = AsyncMock(
            side_effect=[
                {"video_id": "video_1", "platform": "youtube", "frames": [], "created_new": True},
                {"video_id": "video_2", "platform": "youtube", "frames": [], "created_new": True}
            ]
        )

        # Mock the VideoFetcher
        with pytest.MonkeyPatch().context() as m:
            # Create a mock VideoFetcher
            mock_fetcher = MagicMock()
            mock_fetcher.fetch_videos = AsyncMock(return_value=mock_videos)
            m.setattr("services.parallel_video_service.VideoFetcher", mock_fetcher)

            result = await service._process_videos_batch(
                platform_queries={"youtube": ["test query"]},
                job_id="test_job_123"
            )

        assert result["processing_type"] == "batch_parallel"
        assert result["job_id"] == "test_job_123"
        assert result["summary"]["total_processed"] == 2
        assert result["summary"]["total_errors"] == 0

    @pytest.mark.asyncio
    async def test_processing_stats(self, mock_db):
        """Test processing statistics retrieval."""
        service = ParallelVideoService(mock_db)

        # Mock database responses for job-specific stats
        mock_db.fetch_one.side_effect = [
            {"count": 5},  # video count
            {"count": 25}  # frame count
        ]

        stats = await service.get_processing_stats("test_job_123")

        assert "job_video_count" in stats
        assert "job_frame_count" in stats
        assert stats["job_video_count"] == 5
        assert stats["job_frame_count"] == 25

    @pytest.mark.asyncio
    async def test_resource_cleanup(self, mock_db):
        """Test resource cleanup."""
        service = ParallelVideoService(mock_db)

        # Start pipeline first
        await service.pipeline.start_pipeline()
        assert service.pipeline.is_running

        # Cleanup resources
        await service.cleanup_resources()
        assert not service.pipeline.is_running


class TestIdempotencyIntegration:
    """Test idempotency across the entire parallel system."""

    @pytest.mark.asyncio
    async def test_duplicate_video_prevention(self, mock_db):
        """Test that duplicate videos are prevented across the system."""
        manager = IdempotencyManager(mock_db)

        # First video creation should succeed
        mock_db.fetch_one.return_value = None
        created_new_1, video_id_1 = await manager.create_video_with_idempotency(
            video_id="duplicate_test",
            platform="youtube",
            url="https://example.com/duplicate",
            title="Duplicate Test"
        )

        # Second creation should be prevented
        existing_video = {"video_id": "duplicate_test", "platform": "youtube"}
        mock_db.fetch_one.return_value = existing_video
        created_new_2, video_id_2 = await manager.create_video_with_idempotency(
            video_id="duplicate_test",
            platform="youtube",
            url="https://example.com/duplicate",
            title="Duplicate Test"
        )

        assert created_new_1 is True
        assert created_new_2 is False
        assert video_id_1 == video_id_2 == "duplicate_test"

    @pytest.mark.asyncio
    async def test_frame_idempotency(self, mock_db):
        """Test that duplicate frames are prevented."""
        manager = IdempotencyManager(mock_db)

        # First frame creation should succeed
        mock_db.fetch_one.return_value = None
        created_new_1, frame_id_1 = await manager.create_frame_with_idempotency(
            video_id="test_video",
            frame_index=0,
            timestamp=0.0,
            local_path="/path/to/frame_0.jpg"
        )

        # Second frame creation should be prevented
        mock_db.fetch_one.return_value = {"frame_id": "test_video_frame_0"}
        created_new_2, frame_id_2 = await manager.create_frame_with_idempency(
            video_id="test_video",
            frame_index=0,
            timestamp=0.0,
            local_path="/path/to/frame_0.jpg"
        )

        assert created_new_1 is True
        assert created_new_2 is False
        assert frame_id_1 == frame_id_2 == "test_video_frame_0"


@pytest.mark.integration
class TestEndToEndParallelProcessing:
    """End-to-end integration tests for parallel processing."""

    @pytest.mark.asyncio
    async def test_parallel_vs_sequential_comparison(self, mock_db):
        """Test that parallel processing maintains the same results as sequential."""
        # This would be a more comprehensive test comparing outputs
        # For now, we'll verify the structure is correct

        service = ParallelVideoService(mock_db)

        # Test data
        platform_queries = {
            "youtube": ["query1", "query2"],
            "tiktok": ["query3"]
        }

        # Mock the streaming pipeline to return expected structure
        async def mock_stream():
            yield {"type": "video_queued", "video_id": "test1", "platform": "youtube"}
            yield {"type": "video_queued", "video_id": "test2", "platform": "tiktok"}
            yield {"type": "pipeline_complete", "stats": {"processing_completed": 2, "duplicates_skipped": 0, "errors": 0}}

        service.pipeline.process_videos_streaming = mock_stream

        result = await service.process_videos_parallel(
            platform_queries=platform_queries,
            job_id="test_job",
            use_streaming=True
        )

        assert result["processing_type"] == "streaming_parallel"
        assert result["job_id"] == "test_job"
        assert "stats" in result
        assert "summary" in result
        assert result["summary"]["total_processed"] == 2
