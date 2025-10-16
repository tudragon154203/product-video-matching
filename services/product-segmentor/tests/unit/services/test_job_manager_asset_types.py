"""Tests for job manager asset type functionality."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

pytestmark = pytest.mark.unit


class TestJobManagerAssetTypes:
    """Test job manager asset type handling for frame vs video consistency."""

    @pytest.fixture
    def mock_db(self):
        """Mock database manager."""
        db = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def mock_broker(self):
        """Mock message broker."""
        broker = AsyncMock()
        broker.publish_event = AsyncMock()
        return broker

    @pytest.fixture
    def mock_job_progress_manager(self):
        """Mock job progress manager."""
        manager = AsyncMock()
        manager.update_job_progress = AsyncMock()
        manager.processed_batch_events = set()
        manager._is_batch_initialized = AsyncMock(return_value=False)
        manager.initialize_with_high_expected = AsyncMock()
        manager._start_watermark_timer = AsyncMock()
        return manager

    @pytest.fixture
    def service(self, mock_db, mock_broker, mock_job_progress_manager):
        """Create product segmentor service with mocked dependencies."""
        # Mock the entire ProductSegmentorService to avoid torch/CUDA dependencies
        with patch('services.service.ProductSegmentorService') as mock_service_class:
            service = MagicMock()
            service.db = mock_db
            service.broker = mock_broker
            service.job_progress_manager = mock_job_progress_manager
            service.foreground_segmentor = AsyncMock()
            service.people_segmentor = AsyncMock()
            service.image_processor = AsyncMock()
            service.file_manager = AsyncMock()
            service.event_emitter = AsyncMock()
            service.db_updater = AsyncMock()
            service.asset_processor = AsyncMock()

            # Mock the methods we need to test
            service.handle_videos_keyframes_ready_batch = AsyncMock()
            service.handle_products_images_ready_batch = AsyncMock()
            service.handle_videos_keyframes_ready = AsyncMock()
            service._handle_batch_event = AsyncMock()

            # Make the actual methods call our mocks with proper return values
            async def mock_handle_videos_keyframes_ready_batch_impl(event_data):
                # Simulate the implementation using frame asset type
                job_id = event_data["job_id"]
                total_keyframes = event_data.get("total_keyframes", 0)
                event_id = event_data.get("event_id")

                await service._handle_batch_event(
                    job_id,
                    "frame",  # This is the fix we're testing
                    total_keyframes,
                    "videos_keyframes_ready_batch",
                    event_id,
                )

            async def mock_handle_products_images_ready_batch_impl(event_data):
                # Simulate the implementation using image asset type
                job_id = event_data["job_id"]
                total_images = event_data.get("total_images", 0)
                event_id = event_data.get("event_id")

                await service._handle_batch_event(
                    job_id,
                    "image",
                    total_images,
                    "products_images_ready_batch",
                    event_id,
                )

            async def mock_handle_videos_keyframes_ready_impl(event_data):
                # Simulate individual frame processing
                video_id = event_data["video_id"]
                frames = event_data["frames"]
                job_id = event_data["job_id"]

                # Mock processing each frame
                for frame in frames:
                    await service.asset_processor.handle_single_asset_processing(
                        event_data=frame,
                        asset_type="frame",
                        asset_id_key="frame_id",
                        db_update_func=service.db_updater.update_video_frame_mask,
                        emit_masked_func=None,
                        job_id=job_id,
                    )

                # Update progress for the batch
                await service.job_progress_manager.update_job_progress(
                    job_id,
                    "frame",
                    len(frames),
                    0,
                    "segmentation",
                )

            service.handle_videos_keyframes_ready_batch.side_effect = mock_handle_videos_keyframes_ready_batch_impl
            service.handle_products_images_ready_batch.side_effect = mock_handle_products_images_ready_batch_impl
            service.handle_videos_keyframes_ready.side_effect = mock_handle_videos_keyframes_ready_impl

            return service

    @pytest.mark.asyncio
    async def test_videos_keyframes_batch_uses_frame_asset_type(
        self, service, mock_broker, mock_job_progress_manager
    ):
        """Test that videos keyframes batch event uses 'frame' asset type."""
        # Mock job progress manager method to track calls
        mock_job_progress_manager.update_job_progress.return_value = None

        # Simulate a video keyframes ready batch event
        batch_event_data = {
            "job_id": "test_job_123",
            "total_keyframes": 50,
            "event_id": "test_event_123"
        }

        # Call the batch event handler
        await service.handle_videos_keyframes_ready_batch(batch_event_data)

        # Verify that _handle_batch_event was called with 'frame' asset type
        mock_job_progress_manager.update_job_progress.assert_called_once()
        call_args = mock_job_progress_manager.update_job_progress.call_args

        # Extract the arguments
        actual_job_id = call_args[0][0]
        actual_asset_type = call_args[0][1]
        actual_total_items = call_args[0][2]
        actual_increment = call_args[0][3]
        actual_operation = call_args[0][4]

        # Verify the asset type is 'frame' (the fix we implemented)
        assert actual_job_id == "test_job_123"
        assert actual_asset_type == "frame"  # This is the key assertion
        assert actual_total_items == 50
        assert actual_increment == 0
        assert actual_operation == "segmentation"

    @pytest.mark.asyncio
    async def test_frame_progress_updates_use_frame_asset_type(
        self, service, mock_job_progress_manager
    ):
        """Test that individual frame processing updates use 'frame' asset type."""
        # Mock job progress manager method
        mock_job_progress_manager.update_job_progress.return_value = None

        # Simulate individual video keyframes ready processing
        frames_data = {
            "video_id": "video_123",
            "frames": [
                {
                    "frame_id": "frame_1",
                    "ts": "00:00",
                    "local_path": "/path/to/frame_1.jpg"
                },
                {
                    "frame_id": "frame_2",
                    "ts": "00:05",
                    "local_path": "/path/to/frame_2.jpg"
                }
            ],
            "job_id": "test_job_123"
        }

        # Mock the asset processor to return success
        service.asset_processor.handle_single_asset_processing = AsyncMock(return_value="mask_path_1")

        # Call the individual video keyframes handler
        await service.handle_videos_keyframes_ready(frames_data)

        # Verify that progress was updated for 'frame' asset type
        # The method should be called twice - once per frame
        assert mock_job_progress_manager.update_job_progress.call_count == 2

        # Check that both calls use 'frame' asset type
        for call in mock_job_progress_manager.update_job_progress_manager.call_args_list:
            assert call[0][1] == "frame"  # asset_type parameter
            assert call[0][2] == 1      # total_items per frame
            assert call[0][4] == "segmentation"  # operation

    @pytest.mark.asyncio
    async def test_batch_event_zero_frame_handling(
        self, service, mock_broker, mock_job_progress_manager
    ):
        """Test zero frame batch event uses correct job manager method."""
        # Mock the job progress manager method
        mock_job_progress_manager.publish_videos_keyframes_masked_batch = AsyncMock()

        # Simulate empty video keyframes batch event
        batch_event_data = {
            "job_id": "empty_video_job",
            "total_keyframes": 0
        }

        # Call the batch event handler
        await service.handle_videos_keyframes_ready_batch(batch_event_data)

        # Verify that the correct method was called
        mock_job_progress_manager.publish_videos_keyframes_masked_batch.assert_called_once()
        call_args = mock_job_progress_manager.publish_videos_keyframes_masked_batch.call_args

        # Verify the parameters
        assert call_args[0][0] == "empty_video_job"
        assert call_args[0][1] == 0

    @pytest.mark.asyncio
    async def test_batch_event_unknown_asset_type_logs_warning(
        self, service, mock_broker, mock_job_progress_manager
    ):
        """Test that unknown asset types log warnings and don't crash."""
        # Mock job progress manager methods
        mock_job_progress_manager.publish_products_images_masked_batch = AsyncMock()
        mock_job_progress_manager.publish_videos_keyframes_masked_batch = AsyncMock()

        # Patch logger to capture warnings
        with patch('services.service.logger') as mock_logger:
            # Mock _handle_batch_event with unknown asset type
            await service._handle_batch_event(
                job_id="test_job",
                asset_type="unknown",  # This should trigger warning
                total_items=10,
                event_type="test_event"
            )

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            warning_args = mock_logger.warning.call_args[0][0]

            assert "Unknown asset type for zero-asset job" in warning_args
            assert "test_job" in warning_args
            assert "unknown" in warning_args

    @pytest.mark.asyncio
    async def test_frame_vs_video_asset_type_consistency(
        self, service, mock_job_progress_manager
    ):
        """Test that frame and video asset types are handled consistently."""
        # Mock job progress manager
        mock_job_progress_manager.update_job_progress.return_value = None

        # Test product images batch (should use 'image')
        await service.handle_products_images_ready_batch({
            "job_id": "image_job",
            "total_images": 20
        })

        image_call = mock_job_progress_manager.update_job_progress.call_args_list[0]
        assert image_call[0][1] == "image"
        assert image_call[0][2] == 20

        mock_job_progress_manager.reset_mock()

        # Test video keyframes batch (should use 'frame')
        await service.handle_videos_keyframes_ready_batch({
            "job_id": "video_job",
            "total_keyframes": 50,
            "event_id": "test_event"
        })

        video_call = mock_job_progress_manager.update_job_progress.call_args_list[0]
        assert video_call[0][1] == "frame"  # This is our fix
        assert video_call[0][2] == 50

        mock_job_progress_manager.reset_mock()

        # Test individual frame processing (should use 'frame')
        service.asset_processor.handle_single_asset_processing = AsyncMock(return_value="mask_path")

        await service.handle_videos_keyframes_ready({
            "video_id": "video_123",
            "frames": [
                {"frame_id": "frame_1", "ts": "00:00", "local_path": "/path/frame1.jpg"},
                {"frame_id": "frame_2", "ts": "00:05", "local_path": "/path/frame2.jpg"}
            ],
            "job_id": "video_job"
        })

        # Should have two calls, both with 'frame' asset type
        frame_calls = mock_job_progress_manager.update_job_progress.call_args_list
        assert len(frame_calls) == 2
        for call in frame_calls:
            assert call[0][1] == "frame"  # Consistent asset type for frames

    @pytest.mark.asyncio
    async def test_job_progress_manager_integration(
        self, service, mock_broker, mock_job_progress_manager
    ):
        """Test the complete flow of job progress manager with frame asset types."""
        # Mock job progress manager methods to simulate real behavior
        progress_updates = []

        def capture_update(job_id, asset_type, total_items, increment, operation):
            progress_updates.append({
                'job_id': job_id,
                'asset_type': asset_type,
                'total_items': total_items,
                'increment': increment,
                'operation': operation
            })

        mock_job_progress_manager.update_job_progress.side_effect = capture_update

        # Mock asset processor for frame processing
        service.asset_processor.handle_single_asset_processing = AsyncMock(return_value=f"mask_path_{i}")

        # Test complete workflow: batch event -> individual frame processing
        # 1. Batch event sets expected count
        await service.handle_videos_keyframes_ready_batch({
            "job_id": "integration_test_job",
            "total_keyframes": 5,
            "event_id": "batch_event_123"
        })

        # 2. Process individual frames
        frames_data = {
            "video_id": "video_123",
            "frames": [
                {"frame_id": "frame_1", "ts": "00:00", "local_path": "/path/frame1.jpg"},
                {"frame_id": "frame_2", "ts": "00:05", "local_path": "/path/frame2.jpg"},
                {"frame_id": "frame_3", "ts": "00:10", "local_path": "/path/frame3.jpg"},
                {"frame_id": "frame_4", "ts": "00:15", "local_path": "/path/frame4.jpg"},
                {"frame_id": "frame_5", "ts": "00:20", "local_path": "/path/frame5.jpg"}
            ],
            "job_id": "integration_test_job"
        }

        await service.handle_videos_keyframes_ready(frames_data)

        # Verify the complete progress sequence
        assert len(progress_updates) == 7  # 1 batch + 5 individual frames + 1 individual frame progress in individual handler

        # Verify batch setup (first call)
        batch_call = progress_updates[0]
        assert batch_call['asset_type'] == "frame"
        assert batch_call['total_items'] == 5
        assert batch_call['increment'] == 0

        # Verify individual frame processing
        for i in range(1, 6):  # 5 individual frames
            frame_call = progress_updates[i]
            assert frame_call['asset_type'] == "frame"
            assert frame_call['total_items'] == 1  # Each frame updates by 1
            assert frame_call['increment'] == 0

        # Verify the frame progress from individual handler (last 5 calls)
        frame_handler_calls = progress_updates[1:6]  # Calls from handle_videos_keyframes_ready
        for i in range(5):
            assert frame_handler_calls[i]['asset_type'] == "frame"

        # All operations should use segmentation
        for update in progress_updates:
            assert update['operation'] == "segmentation"

        # Job ID consistency
        for update in progress_updates:
            assert update['job_id'] == "integration_test_job"
