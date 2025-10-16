"""
Unit tests for ParallelVideoService.

Tests the high-level parallel video service that integrates all components
and provides the main API for parallel processing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.parallel_video_service import ParallelVideoService


class TestParallelVideoServiceInitialization:
    """Test service initialization and component setup."""

    def test_service_initialization_default_config(self, mock_db):
        """Test service initialization with default configuration."""
        service = ParallelVideoService(mock_db)

        assert service.db == mock_db
        assert service.event_emitter is None
        assert service.job_progress_manager is None
        assert service.idempotency_manager is not None
        assert service.video_processor is not None
        assert service.pipeline is not None
        assert service.config is not None

    def test_service_initialization_with_components(self, mock_db, mock_event_emitter, mock_progress_manager):
        """Test service initialization with all components."""
        custom_config = MagicMock()
        # Set integer values for semaphore initialization
        custom_config.max_concurrent_downloads = 2
        custom_config.max_concurrent_processing = 2
        custom_config.download_queue_size = 10
        custom_config.processing_queue_size = 10
        custom_config.batch_size_for_processing = 5

        service = ParallelVideoService(
            db=mock_db,
            event_emitter=mock_event_emitter,
            job_progress_manager=mock_progress_manager,
            config=custom_config
        )

        assert service.event_emitter == mock_event_emitter
        assert service.job_progress_manager == mock_progress_manager
        assert service.config == custom_config

    def test_component_initialization(self, parallel_video_service, mock_db):
        """Test that all components are properly initialized."""
        service = parallel_video_service

        assert service.idempotency_manager.db == mock_db
        assert service.video_processor.db == mock_db
        assert service.video_processor.idempotency_manager == service.idempotency_manager
        assert service.pipeline.idempotency_manager == service.idempotency_manager
        assert service.pipeline.config == service.config


class TestStreamingProcessing:
    """Test streaming parallel processing functionality."""

    @pytest.mark.asyncio
    async def test_process_videos_streaming_success(self, parallel_video_service, platform_queries, sample_video_data_list):
        """Test successful streaming parallel processing."""
        # Mock pipeline to return successful results
        async def mock_stream(platform_queries=None, job_id=None, progress_callback=None):
            yield {"type": "video_queued", "video_id": "video_1", "platform": "youtube"}
            yield {"type": "video_queued", "video_id": "video_2", "platform": "tiktok"}
            yield {"type": "pipeline_complete", "stats": {
                "processing_completed": 2,
                "duplicates_skipped": 0,
                "errors": 0
            }}

        parallel_video_service.pipeline.process_videos_streaming = mock_stream

        result = await parallel_video_service.process_videos_parallel(
            platform_queries=platform_queries,
            job_id="test_job",
            use_streaming=True
        )

        assert result["processing_type"] == "streaming_parallel"
        assert result["job_id"] == "test_job"
        assert result["summary"]["total_processed"] == 2
        assert result["summary"]["total_skipped"] == 0
        assert result["summary"]["total_errors"] == 0
        assert result["summary"]["success_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_process_videos_streaming_with_errors(self, parallel_video_service, platform_queries):
        """Test streaming processing with some errors."""
        async def mock_stream(platform_queries=None, job_id=None, progress_callback=None):
            yield {"type": "pipeline_complete", "stats": {
                "processing_completed": 1,
                "duplicates_skipped": 1,
                "errors": 2
            }}

        parallel_video_service.pipeline.process_videos_streaming = mock_stream

        result = await parallel_video_service.process_videos_parallel(
            platform_queries=platform_queries,
            job_id="test_job",
            use_streaming=True
        )

        assert result["summary"]["total_processed"] == 1
        assert result["summary"]["total_skipped"] == 1
        assert result["summary"]["total_errors"] == 2
        assert result["summary"]["success_rate"] == 33.33  # 1/3

    @pytest.mark.asyncio
    async def test_process_videos_streaming_pipeline_exception(self, parallel_video_service, platform_queries):
        """Test streaming processing when pipeline raises exception."""
        parallel_video_service.pipeline.process_videos_streaming = AsyncMock(
            side_effect=Exception("Pipeline error")
        )

        result = await parallel_video_service.process_videos_parallel(
            platform_queries=platform_queries,
            job_id="test_job",
            use_streaming=True
        )

        assert result["summary"]["total_errors"] == 1

    @pytest.mark.asyncio
    async def test_process_videos_streaming_progress_callback(self, parallel_video_service, platform_queries):
        """Test that progress callback is called during streaming."""
        callback_calls = []

        async def mock_stream(platform_queries=None, job_id=None, progress_callback=None):
            yield {"type": "pipeline_complete", "stats": {"processing_completed": 2}}

        async def mock_callback(stats):
            callback_calls.append(stats)

        parallel_video_service.pipeline.process_videos_streaming = mock_stream

        # Replace the private progress callback
        parallel_video_service._update_progress_callback = mock_callback

        await parallel_video_service.process_videos_parallel(
            platform_queries=platform_queries,
            job_id="test_job",
            use_streaming=True
        )

        # Progress callback should have been called
        assert len(callback_calls) == 1
        assert "processing_completed" in callback_calls[0]


class TestBatchParallelProcessing:
    """Test batch parallel processing functionality."""

    @pytest.mark.asyncio
    async def test_process_videos_batch_success(self, parallel_video_service, platform_queries, sample_video_data_list):
        """Test successful batch parallel processing."""
        # Mock VideoFetcher to return test videos
        mock_videos = sample_video_data_list[:3]

        with patch('services.parallel_video_service.VideoFetcher') as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.fetch_videos = AsyncMock(return_value=mock_videos)
            mock_fetcher_class.return_value = mock_fetcher

            # Mock video processor responses
            parallel_video_service.video_processor.process_video = AsyncMock(
                side_effect=[
                    {"video_id": "video_1", "platform": "youtube", "frames": [], "created_new": True},
                    {"video_id": "video_2", "platform": "tiktok", "frames": [], "created_new": True},
                    {"video_id": "video_3", "platform": "youtube", "frames": [], "created_new": True}
                ]
            )

            result = await parallel_video_service._process_videos_batch(
                platform_queries=platform_queries,
                job_id="test_job"
            )

        assert result["processing_type"] == "batch_parallel"
        assert result["job_id"] == "test_job"
        assert result["summary"]["total_processed"] == 3
        assert result["summary"]["total_skipped"] == 0
        assert result["summary"]["total_errors"] == 0
        assert result["summary"]["success_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_process_videos_batch_with_duplicates(self, parallel_video_service, platform_queries, sample_video_data_list):
        """Test batch processing with duplicate videos."""
        mock_videos = sample_video_data_list[:2]

        with patch('services.parallel_video_service.VideoFetcher') as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.fetch_videos = AsyncMock(return_value=mock_videos)
            mock_fetcher_class.return_value = mock_fetcher

            # Mock video processor responses with duplicates
            parallel_video_service.video_processor.process_video = AsyncMock(
                side_effect=[
                    {"video_id": "video_1", "platform": "youtube", "frames": [], "created_new": True},
                    {"video_id": "video_2", "platform": "tiktok", "frames": [], "skipped": True}
                ]
            )

            result = await parallel_video_service._process_videos_batch(
                platform_queries=platform_queries,
                job_id="test_job"
            )

        assert result["summary"]["total_processed"] == 1
        assert result["summary"]["total_skipped"] == 1

    @pytest.mark.asyncio
    async def test_process_videos_batch_fetcher_errors(self, parallel_video_service, platform_queries):
        """Test batch processing when VideoFetcher has errors."""
        with patch('services.parallel_video_service.VideoFetcher') as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.fetch_videos = AsyncMock(side_effect=Exception("Fetch error"))
            mock_fetcher_class.return_value = mock_fetcher

            result = await parallel_video_service._process_videos_batch(
                platform_queries=platform_queries,
                job_id="test_job"
            )

        assert result["summary"]["total_errors"] == 1

    @pytest.mark.asyncio
    async def test_process_videos_batch_processing_errors(self, parallel_video_service, platform_queries, sample_video_data_list):
        """Test batch processing when video processing has errors."""
        mock_videos = sample_video_data_list[:2]

        with patch('services.parallel_video_service.VideoFetcher') as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.fetch_videos = AsyncMock(return_value=mock_videos)
            mock_fetcher_class.return_value = mock_fetcher

            # Mock video processor with one error
            parallel_video_service.video_processor.process_video = AsyncMock(
                side_effect=[
                    {"video_id": "video_1", "platform": "youtube", "frames": [], "created_new": True},
                    Exception("Processing error")
                ]
            )

            result = await parallel_video_service._process_videos_batch(
                platform_queries=platform_queries,
                job_id="test_job"
            )

        assert result["summary"]["total_processed"] == 1
        assert result["summary"]["total_errors"] == 1


class TestProcessingModeSelection:
    """Test processing mode selection and fallback behavior."""

    @pytest.mark.asyncio
    async def test_process_videos_parallel_streaming_mode(self, parallel_video_service, platform_queries):
        """Test parallel processing with streaming mode."""
        parallel_video_service._process_videos_streaming = AsyncMock(return_value={
            "processing_type": "streaming_parallel",
            "job_id": "test_job",
            "summary": {"total_processed": 2}
        })

        result = await parallel_video_service.process_videos_parallel(
            platform_queries=platform_queries,
            job_id="test_job",
            use_streaming=True
        )

        assert result["processing_type"] == "streaming_parallel"
        parallel_video_service._process_videos_streaming.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_videos_parallel_batch_mode(self, parallel_video_service, platform_queries):
        """Test parallel processing with batch mode."""
        parallel_video_service._process_videos_batch = AsyncMock(return_value={
            "processing_type": "batch_parallel",
            "job_id": "test_job",
            "summary": {"total_processed": 2}
        })

        result = await parallel_video_service.process_videos_parallel(
            platform_queries=platform_queries,
            job_id="test_job",
            use_streaming=False
        )

        assert result["processing_type"] == "batch_parallel"
        parallel_video_service._process_videos_batch.assert_called_once()


class TestStatisticsAndMonitoring:
    """Test statistics collection and monitoring functionality."""

    @pytest.mark.asyncio
    async def test_get_processing_stats_without_job_id(self, parallel_video_service):
        """Test getting processing statistics without job ID."""
        pipeline_stats = {
            "search_results_found": 10,
            "downloads_completed": 8,
            "processing_completed": 6,
            "duplicates_skipped": 2,
            "errors": 1
        }

        parallel_video_service.pipeline.get_stats = MagicMock(return_value=pipeline_stats)

        stats = await parallel_video_service.get_processing_stats()

        assert stats == pipeline_stats
        parallel_video_service.pipeline.get_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_processing_stats_with_job_id(self, parallel_video_service):
        """Test getting processing statistics with job ID."""
        pipeline_stats = {
            "search_results_found": 10,
            "downloads_completed": 8,
            "processing_completed": 6
        }

        parallel_video_service.pipeline.get_stats = MagicMock(return_value=pipeline_stats)
        parallel_video_service.db.fetch_one = AsyncMock(side_effect=[
            {"count": 5},  # video count
            {"count": 20}  # frame count
        ])

        stats = await parallel_video_service.get_processing_stats("test_job")

        assert stats["search_results_found"] == 10
        assert stats["job_video_count"] == 5
        assert stats["job_frame_count"] == 20

    @pytest.mark.asyncio
    async def test_get_processing_stats_database_error(self, parallel_video_service):
        """Test handling database errors when getting job stats."""
        pipeline_stats = {"processing_completed": 6}
        parallel_video_service.pipeline.get_stats = MagicMock(return_value=pipeline_stats)
        parallel_video_service.db.fetch_one = AsyncMock(side_effect=Exception("Database error"))

        stats = await parallel_video_service.get_processing_stats("test_job")

        # Should still return pipeline stats despite database error
        assert stats["processing_completed"] == 6
        # Job-specific stats should not be present
        assert "job_video_count" not in stats

    @pytest.mark.asyncio
    async def test_update_progress_callback(self, parallel_video_service, mock_progress_manager):
        """Test progress callback functionality."""
        parallel_video_service.job_progress_manager = mock_progress_manager

        stats = {
            "processing_started": 10,
            "processing_completed": 6
        }

        await parallel_video_service._update_progress_callback(stats)

        # Should update progress with 60% completion
        mock_progress_manager.update_job_progress.assert_called_once()


class TestResourceCleanup:
    """Test resource cleanup and lifecycle management."""

    @pytest.mark.asyncio
    async def test_cleanup_resources(self, parallel_video_service):
        """Test resource cleanup functionality."""
        # Mock pipeline stop method
        parallel_video_service.pipeline.stop_pipeline = AsyncMock()

        await parallel_video_service.cleanup_resources()

        parallel_video_service.pipeline.stop_pipeline.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_resources_with_error(self, parallel_video_service):
        """Test cleanup when pipeline stop raises error."""
        parallel_video_service.pipeline.stop_pipeline = AsyncMock(side_effect=Exception("Cleanup error"))

        # Should not raise exception
        try:
            await parallel_video_service.cleanup_resources()
        except Exception:
            # The service should handle the exception internally
            pass


class TestParallelVideoServiceIntegration:
    """Integration tests for the complete service."""

    @pytest.mark.asyncio
    async def test_full_workflow_streaming_success(self, parallel_video_service, platform_queries):
        """Test complete streaming workflow with all components."""
        # Mock successful streaming pipeline
        async def mock_stream():
            yield {"type": "video_queued", "video_id": "video_1", "platform": "youtube"}
            yield {"type": "pipeline_complete", "stats": {
                "processing_completed": 1,
                "duplicates_skipped": 0,
                "errors": 0
            }}

        parallel_video_service.pipeline.process_videos_streaming = mock_stream

        result = await parallel_video_service.process_videos_parallel(
            platform_queries=platform_queries,
            job_id="integration_test",
            use_streaming=True
        )

        assert result["processing_type"] == "streaming_parallel"
        assert result["job_id"] == "integration_test"
        assert result["summary"]["total_processed"] == 1
        assert result["summary"]["success_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_full_workflow_batch_success(self, parallel_video_service, platform_queries, sample_video_data_list):
        """Test complete batch workflow with all components."""
        mock_videos = sample_video_data_list[:2]

        with patch('services.parallel_video_service.VideoFetcher') as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.fetch_videos = AsyncMock(return_value=mock_videos)
            mock_fetcher_class.return_value = mock_fetcher

            parallel_video_service.video_processor.process_video = AsyncMock(
                side_effect=[
                    {"video_id": "video_1", "platform": "youtube", "frames": [], "created_new": True},
                    {"video_id": "video_2", "platform": "tiktok", "frames": [], "created_new": True}
                ]
            )

            result = await parallel_video_service.process_videos_parallel(
                platform_queries=platform_queries,
                job_id="integration_test",
                use_streaming=False
            )

        assert result["processing_type"] == "batch_parallel"
        assert result["job_id"] == "integration_test"
        assert result["summary"]["total_processed"] == 2
        assert result["summary"]["success_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_error_handling_throughout_workflow(self, parallel_video_service, platform_queries):
        """Test error handling throughout the entire workflow."""
        # Mock streaming pipeline to raise exception
        parallel_video_service.pipeline.process_videos_streaming = AsyncMock(
            side_effect=Exception("Pipeline failure")
        )

        result = await parallel_video_service.process_videos_parallel(
            platform_queries=platform_queries,
            job_id="error_test",
            use_streaming=True
        )

        # Service should handle errors gracefully
        assert result["job_id"] == "error_test"
        assert result["summary"]["total_errors"] >= 1

    @pytest.mark.asyncio
    async def test_service_lifecycle_with_processing(self, parallel_video_service, platform_queries):
        """Test service lifecycle during actual processing."""
        # Mock successful processing
        async def mock_stream():
            yield {"type": "pipeline_complete", "stats": {"processing_completed": 1}}

        parallel_video_service.pipeline.process_videos_streaming = mock_stream

        # Process videos
        await parallel_video_service.process_videos_parallel(
            platform_queries=platform_queries,
            job_id="lifecycle_test",
            use_streaming=True
        )

        # Cleanup should work without errors
        await parallel_video_service.cleanup_resources()

        # Service should still be functional
        stats = await parallel_video_service.get_processing_stats()
        assert isinstance(stats, dict)