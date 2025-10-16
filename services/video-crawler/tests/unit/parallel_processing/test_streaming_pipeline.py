"""
Unit tests for StreamingVideoPipeline.

Tests async streaming pipeline functionality including worker management,
queue operations, and parallel processing coordination.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from collections import defaultdict

from services.streaming_pipeline import StreamingVideoPipeline, PipelineConfig, VideoTask


class TestPipelineInitialization:
    """Test pipeline initialization and configuration."""

    def test_pipeline_initialization_default_config(self, mock_db):
        """Test pipeline initialization with default configuration."""
        pipeline = StreamingVideoPipeline(mock_db)

        assert pipeline.db == mock_db
        assert isinstance(pipeline.config, PipelineConfig)
        assert pipeline.config.max_concurrent_downloads == 5  # Default value
        assert pipeline.config.max_concurrent_processing == 3  # Default value
        assert not pipeline.is_running
        assert len(pipeline.download_workers) == 0
        assert len(pipeline.processing_workers) == 0

    def test_pipeline_initialization_custom_config(self, mock_db, pipeline_config):
        """Test pipeline initialization with custom configuration."""
        pipeline = StreamingVideoPipeline(mock_db, pipeline_config)

        assert pipeline.config == pipeline_config
        assert pipeline.download_queue.maxsize == pipeline_config.download_queue_size
        assert pipeline.processing_queue.maxsize == pipeline_config.processing_queue_size

    def test_statistics_initialization(self, mock_db, pipeline_config):
        """Test that statistics are properly initialized."""
        pipeline = StreamingVideoPipeline(mock_db, pipeline_config)

        stats = pipeline.get_stats()
        assert stats["search_results_found"] == 0
        assert stats["downloads_completed"] == 0
        assert stats["processing_completed"] == 0
        assert stats["duplicates_skipped"] == 0
        assert stats["errors"] == 0


class TestPipelineLifecycle:
    """Test pipeline start/stop lifecycle management."""

    @pytest.mark.asyncio
    async def test_start_pipeline(self, streaming_pipeline):
        """Test starting pipeline creates workers."""
        await streaming_pipeline.start_pipeline()

        assert streaming_pipeline.is_running
        assert len(streaming_pipeline.download_workers) == streaming_pipeline.config.max_concurrent_downloads
        assert len(streaming_pipeline.processing_workers) == streaming_pipeline.config.max_concurrent_processing

        # Verify workers are asyncio Tasks
        for worker in streaming_pipeline.download_workers + streaming_pipeline.processing_workers:
            assert isinstance(worker, asyncio.Task)

        await streaming_pipeline.stop_pipeline()

    @pytest.mark.asyncio
    async def test_start_pipeline_already_running(self, streaming_pipeline):
        """Test starting already running pipeline doesn't create duplicate workers."""
        await streaming_pipeline.start_pipeline()
        initial_download_workers = len(streaming_pipeline.download_workers)
        initial_processing_workers = len(streaming_pipeline.processing_workers)

        # Try to start again
        await streaming_pipeline.start_pipeline()

        assert len(streaming_pipeline.download_workers) == initial_download_workers
        assert len(streaming_pipeline.processing_workers) == initial_processing_workers

        await streaming_pipeline.stop_pipeline()

    @pytest.mark.asyncio
    async def test_stop_pipeline(self, streaming_pipeline):
        """Test stopping pipeline cancels workers."""
        await streaming_pipeline.start_pipeline()
        assert streaming_pipeline.is_running

        await streaming_pipeline.stop_pipeline()

        assert not streaming_pipeline.is_running
        assert len(streaming_pipeline.download_workers) == 0
        assert len(streaming_pipeline.processing_workers) == 0

    @pytest.mark.asyncio
    async def test_stop_pipeline_not_running(self, streaming_pipeline):
        """Test stopping pipeline that's not running is safe."""
        await streaming_pipeline.stop_pipeline()  # Should not raise exception

        assert not streaming_pipeline.is_running
        assert len(streaming_pipeline.download_workers) == 0
        assert len(streaming_pipeline.processing_workers) == 0


class TestTaskPriorityCalculation:
    """Test task priority calculation logic."""

    def test_calculate_priority_short_video(self, streaming_pipeline):
        """Test short videos get high priority."""
        short_video = {"duration_s": 20}
        priority = streaming_pipeline._calculate_priority(short_video)
        assert priority == 3

    def test_calculate_priority_medium_video(self, streaming_pipeline):
        """Test medium videos get medium priority."""
        medium_video = {"duration_s": 60}
        priority = streaming_pipeline._calculate_priority(medium_video)
        assert priority == 2

    def test_calculate_priority_long_video(self, streaming_pipeline):
        """Test long videos get low priority."""
        long_video = {"duration_s": 300}
        priority = streaming_pipeline._calculate_priority(long_video)
        assert priority == 1

    def test_calculate_priority_no_duration(self, streaming_pipeline):
        """Test videos without duration get default priority."""
        video_no_duration = {"title": "Test Video"}
        priority = streaming_pipeline._calculate_priority(video_no_duration)
        assert priority == 1  # Default priority

    def test_calculate_priority_zero_duration(self, streaming_pipeline):
        """Test videos with zero duration get default priority."""
        zero_duration = {"duration_s": 0}
        priority = streaming_pipeline._calculate_priority(zero_duration)
        assert priority == 1


class TestQueueOperations:
    """Test queue operations and task management."""

    @pytest.mark.asyncio
    async def test_video_task_creation(self, sample_video_data):
        """Test VideoTask dataclass creation."""
        task = VideoTask(
            video_data=sample_video_data,
            job_id="test_job",
            platform="youtube",
            priority=2
        )

        assert task.video_data == sample_video_data
        assert task.job_id == "test_job"
        assert task.platform == "youtube"
        assert task.priority == 2

    @pytest.mark.asyncio
    async def test_queue_put_get_operations(self, streaming_pipeline, sample_video_data):
        """Test basic queue put/get operations."""
        task = VideoTask(
            video_data=sample_video_data,
            job_id="test_job",
            platform="youtube"
        )

        # Put task in download queue
        await streaming_pipeline.download_queue.put(task)
        assert not streaming_pipeline.download_queue.empty()

        # Get task from download queue
        retrieved_task = await streaming_pipeline.download_queue.get()
        assert retrieved_task == task
        assert retrieved_task.video_data == sample_video_data

    @pytest.mark.asyncio
    async def test_queue_full_handling(self, streaming_pipeline, sample_video_data_list):
        """Test handling of full queues."""
        # Fill the download queue to capacity
        for video_data in sample_video_data_list[:streaming_pipeline.config.download_queue_size]:
            task = VideoTask(video_data=video_data, job_id="test_job", platform="youtube")
            await streaming_pipeline.download_queue.put(task)

        # Queue should be full now
        assert streaming_pipeline.download_queue.full()

        # Trying to put another task should raise QueueFull
        with pytest.raises(asyncio.QueueFull):
            streaming_pipeline.download_queue.put_nowait(
                VideoTask(video_data=sample_video_data_list[-1], job_id="test_job", platform="youtube")
            )


class TestWorkerFunctionality:
    """Test worker functionality and error handling."""

    @pytest.mark.asyncio
    async def test_download_worker_with_valid_task(self, streaming_pipeline, sample_video_data):
        """Test download worker processes valid task correctly."""
        # Mock the download methods
        streaming_pipeline._check_existing_file = MagicMock(return_value=None)
        streaming_pipeline._download_video_file = AsyncMock(return_value="/path/to/downloaded.mp4")
        streaming_pipeline.processing_queue.put = AsyncMock()

        task = VideoTask(video_data=sample_video_data, job_id="test_job", platform="youtube")

        # Simulate worker processing
        await streaming_pipeline._download_video(task)

        # Verify task was queued for processing
        streaming_pipeline.processing_queue.put.assert_called_once_with(task)
        assert streaming_pipeline.stats["downloads_completed"] == 1

    @pytest.mark.asyncio
    async def test_download_worker_with_existing_file(self, streaming_pipeline, sample_video_data):
        """Test download worker handles existing file correctly."""
        existing_path = "/path/to/existing.mp4"
        streaming_pipeline._check_existing_file = MagicMock(return_value=existing_path)
        streaming_pipeline.processing_queue.put = AsyncMock()

        task = VideoTask(video_data=sample_video_data, job_id="test_job", platform="youtube")

        await streaming_pipeline._download_video(task)

        # Verify video data was updated with existing path
        assert task.video_data["local_path"] == existing_path
        streaming_pipeline.processing_queue.put.assert_called_once_with(task)

    @pytest.mark.asyncio
    async def test_download_worker_with_duplicate_video(self, streaming_pipeline, sample_video_data):
        """Test download worker skips duplicate videos."""
        # Mock idempotency manager to return existing video
        streaming_pipeline.idempotency_manager.check_video_exists = AsyncMock(return_value=True)

        # Mock the processing queue put method
        original_put = streaming_pipeline.processing_queue.put
        streaming_pipeline.processing_queue.put = MagicMock()

        task = VideoTask(video_data=sample_video_data, job_id="test_job", platform="youtube")

        await streaming_pipeline._download_video(task)

        # Verify task was not queued for processing
        streaming_pipeline.processing_queue.put.assert_not_called()
        assert streaming_pipeline.stats["duplicates_skipped"] == 1

        # Restore original method
        streaming_pipeline.processing_queue.put = original_put

    @pytest.mark.asyncio
    async def test_download_worker_download_failure(self, streaming_pipeline, sample_video_data):
        """Test download worker handles download failure gracefully."""
        streaming_pipeline._check_existing_file = MagicMock(return_value=None)
        streaming_pipeline._download_video_file = AsyncMock(return_value=None)  # Download failed

        task = VideoTask(video_data=sample_video_data, job_id="test_job", platform="youtube")

        await streaming_pipeline._download_video(task)

        # Verify task was not queued for processing
        streaming_pipeline.processing_queue.put.assert_not_called()
        assert streaming_pipeline.stats["errors"] == 1

    @pytest.mark.asyncio
    async def test_processing_worker_with_valid_task(self, streaming_pipeline, sample_video_data):
        """Test processing worker processes valid task correctly."""
        # Mock the processing methods
        streaming_pipeline.idempotency_manager.create_video_with_idempotency = AsyncMock(return_value=(True, "video_123"))
        streaming_pipeline.idempotency_manager.get_existing_frames = AsyncMock(return_value=[])
        streaming_pipeline._extract_keyframes_with_idempotency = AsyncMock(return_value=[])

        task = VideoTask(video_data=sample_video_data, job_id="test_job", platform="youtube")

        await streaming_pipeline._process_video(task)

        assert streaming_pipeline.stats["processing_completed"] == 1

    @pytest.mark.asyncio
    async def test_processing_worker_with_duplicate_video(self, streaming_pipeline, sample_video_data):
        """Test processing worker handles duplicate video correctly."""
        # Mock idempotency manager to return existing video with frames
        streaming_pipeline.idempotency_manager.create_video_with_idempotency = AsyncMock(return_value=(False, "existing_video"))
        streaming_pipeline.idempotency_manager.get_existing_frames = AsyncMock(return_value=[
            {"frame_id": "existing_frame", "ts": 0.0, "local_path": "/path/to/frame.jpg"}
        ])

        task = VideoTask(video_data=sample_video_data, job_id="test_job", platform="youtube")

        await streaming_pipeline._process_video(task)

        assert streaming_pipeline.stats["duplicates_skipped"] == 1
        assert streaming_pipeline.stats["processing_completed"] == 0

    @pytest.mark.asyncio
    async def test_worker_error_handling(self, streaming_pipeline, sample_video_data):
        """Test worker handles exceptions gracefully."""
        # Mock method to raise exception
        streaming_pipeline.idempotency_manager.create_video_with_idempotency = AsyncMock(side_effect=Exception("Database error"))

        task = VideoTask(video_data=sample_video_data, job_id="test_job", platform="youtube")

        # Should not raise exception
        await streaming_pipeline._process_video(task)

        assert streaming_pipeline.stats["errors"] == 1


class TestSearchAndStreamResults:
    """Test search and stream functionality."""

    @pytest.mark.asyncio
    async def test_search_and_stream_success(self, streaming_pipeline, sample_video_data_list, platform_queries):
        """Test successful search and stream results."""
        # Mock video fetcher
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_videos = AsyncMock(return_value=sample_video_data_list)

        with patch('services.streaming_pipeline.VideoFetcher', return_value=mock_fetcher):
            await streaming_pipeline._search_and_stream_results("youtube", ["test query"], "job_123")

        # Verify all videos were queued
        assert streaming_pipeline.stats["search_results_found"] == len(sample_video_data_list)

    @pytest.mark.asyncio
    async def test_search_and_stream_queue_full(self, streaming_pipeline, sample_video_data_list, platform_queries):
        """Test search handles full queue gracefully."""
        # Fill download queue
        for _ in range(streaming_pipeline.config.download_queue_size):
            await streaming_pipeline.download_queue.put(None)  # Fill with None values

        initial_errors = streaming_pipeline.stats["errors"]

        # Mock video fetcher to return many videos
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_videos = AsyncMock(return_value=sample_video_data_list * 2)

        with patch('services.streaming_pipeline.VideoFetcher', return_value=mock_fetcher):
            await streaming_pipeline._search_and_stream_results("youtube", ["test query"], "job_123")

        # Verify errors were recorded for dropped videos
        assert streaming_pipeline.stats["errors"] > initial_errors

    @pytest.mark.asyncio
    async def test_search_and_stream_fetcher_error(self, streaming_pipeline, platform_queries):
        """Test search handles fetcher errors gracefully."""
        # Mock video fetcher to raise exception
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_videos = AsyncMock(side_effect=Exception("Search failed"))

        initial_errors = streaming_pipeline.stats["errors"]

        with patch('services.streaming_pipeline.VideoFetcher', return_value=mock_fetcher):
            await streaming_pipeline._search_and_stream_results("youtube", ["test query"], "job_123")

        assert streaming_pipeline.stats["errors"] > initial_errors


class TestPipelineIntegration:
    """Integration tests for the complete pipeline."""

    @pytest.mark.asyncio
    async def test_process_videos_streaming_integration(self, streaming_pipeline, sample_video_data_list, platform_queries):
        """Test complete streaming process integration."""
        # Mock all external dependencies
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_videos = AsyncMock(return_value=sample_video_data_list)

        streaming_pipeline._download_video = AsyncMock()
        streaming_pipeline._process_video = AsyncMock()

        with patch('services.streaming_pipeline.VideoFetcher', return_value=mock_fetcher):
            results = []
            async for result in streaming_pipeline.process_videos_streaming(
                platform_queries=platform_queries,
                job_id="test_job"
            ):
                results.append(result)

        # Verify pipeline completed
        assert any(result.get("type") == "pipeline_complete" for result in results)
        assert streaming_pipeline.stats["search_results_found"] > 0

    @pytest.mark.asyncio
    async def test_pipeline_statistics_accuracy(self, streaming_pipeline, sample_video_data_list):
        """Test that pipeline statistics are accurately tracked."""
        # Start pipeline to enable statistics tracking
        await streaming_pipeline.start_pipeline()

        # Add some tasks and process them
        for video_data in sample_video_data_list[:3]:
            task = VideoTask(video_data=video_data, job_id="test_job", platform="youtube")
            await streaming_pipeline.download_queue.put(task)

        # Update statistics manually to simulate processing
        streaming_pipeline.stats["downloads_started"] = 3
        streaming_pipeline.stats["downloads_completed"] = 2
        streaming_pipeline.stats["processing_started"] = 2
        streaming_pipeline.stats["processing_completed"] = 2
        streaming_pipeline.stats["duplicates_skipped"] = 1

        stats = streaming_pipeline.get_stats()

        assert stats["downloads_started"] == 3
        assert stats["downloads_completed"] == 2
        assert stats["processing_started"] == 2
        assert stats["processing_completed"] == 2
        assert stats["duplicates_skipped"] == 1

        await streaming_pipeline.stop_pipeline()

    @pytest.mark.asyncio
    async def test_pipeline_graceful_shutdown(self, streaming_pipeline, sample_video_data):
        """Test pipeline shuts down gracefully with pending tasks."""
        await streaming_pipeline.start_pipeline()

        # Add some tasks to queues
        task = VideoTask(video_data=sample_video_data, job_id="test_job", platform="youtube")
        await streaming_pipeline.download_queue.put(task)
        await streaming_pipeline.processing_queue.put(task)

        # Stop pipeline - should handle pending tasks gracefully
        await streaming_pipeline.stop_pipeline()

        assert not streaming_pipeline.is_running
        assert len(streaming_pipeline.download_workers) == 0
        assert len(streaming_pipeline.processing_workers) == 0


class TestPipelineErrorRecovery:
    """Test pipeline error recovery and resilience."""

    @pytest.mark.asyncio
    async def test_pipeline_continues_after_worker_failure(self, streaming_pipeline, sample_video_data_list):
        """Test pipeline continues operating when individual workers fail."""
        await streaming_pipeline.start_pipeline()

        # Mock some methods to fail intermittently
        call_count = 0

        async def failing_download(task):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 calls
                raise Exception("Worker failure")
            return True

        streaming_pipeline._download_video = failing_download

        # Add multiple tasks
        for video_data in sample_video_data_list:
            task = VideoTask(video_data=video_data, job_id="test_job", platform="youtube")
            await streaming_pipeline.download_queue.put(task)

        # Wait for processing and add sentinel values to stop workers
        for _ in range(streaming_pipeline.config.max_concurrent_downloads):
            await streaming_pipeline.download_queue.put(None)

        await streaming_pipeline.download_queue.join()

        # Pipeline should have recorded errors but continued
        assert streaming_pipeline.stats["errors"] >= 2

        await streaming_pipeline.stop_pipeline()

    @pytest.mark.asyncio
    async def test_pipeline_handles_database_connection_failure(self, streaming_pipeline, sample_video_data):
        """Test pipeline handles database connection failures gracefully."""
        # Mock idempotency manager to raise database errors
        streaming_pipeline.idempotency_manager.check_video_exists = AsyncMock(side_effect=Exception("Connection lost"))

        task = VideoTask(video_data=sample_video_data, job_id="test_job", platform="youtube")

        # Should not raise exception
        await streaming_pipeline._download_video(task)

        # Error should be recorded
        assert streaming_pipeline.stats["errors"] >= 1
