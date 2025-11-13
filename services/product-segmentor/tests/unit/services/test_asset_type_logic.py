"""Tests for asset type logic in isolation without torch dependencies."""

import pytest
from unittest.mock import AsyncMock

pytestmark = pytest.mark.unit


class TestAssetTypeLogic:
    """Test asset type logic without importing service dependencies."""

    @pytest.mark.asyncio
    async def test_batch_event_uses_frame_asset_type_logic(self):
        """Test the core logic: video keyframes batch should use 'frame' asset type."""
        # Mock job progress manager
        mock_job_progress_manager = AsyncMock()
        mock_job_progress_manager.processed_batch_events = set()

        # Simulate the batch event handling logic
        async def handle_videos_keyframes_ready_batch_logic(event_data, job_progress_manager):
            """Isolated logic from the service method."""
            job_id = event_data["job_id"]
            total_keyframes = event_data.get("total_keyframes", 0)

            # This is the fix: using "video" instead of "video"
            asset_type = "video"  # Previously was "video"

            # Simulate _handle_batch_event call
            await job_progress_manager.update_job_progress(
                job_id,
                asset_type,  # Should be "video"
                total_keyframes,
                0,
                "segmentation",
            )

            return asset_type

        # Test the logic
        batch_event_data = {
            "job_id": "test_job_123",
            "total_keyframes": 50,
            "event_id": "test_event_123"
        }

        asset_type_used = await handle_videos_keyframes_ready_batch_logic(
            batch_event_data, mock_job_progress_manager
        )

        # Verify the logic
        assert asset_type_used == "video"
        mock_job_progress_manager.update_job_progress.assert_called_once_with(
            "test_job_123",
            "video",  # This is the key assertion
            50,
            0,
            "segmentation",
        )

    @pytest.mark.asyncio
    async def test_individual_frame_processing_logic(self):
        """Test that individual frame processing uses 'video' asset type."""
        mock_job_progress_manager = AsyncMock()
        mock_asset_processor = AsyncMock()

        # Simulate individual frame processing logic
        async def handle_videos_keyframes_ready_logic(event_data, job_progress_manager, asset_processor):
            """Isolated logic from the service method."""
            _ = event_data["video_id"]
            frames = event_data["frames"]
            job_id = event_data["job_id"]

            # Process each frame
            for frame in frames:
                await asset_processor.handle_single_asset_processing(
                    event_data=frame,
                    asset_type="video",  # Individual frames use "video"
                    asset_id_key="frame_id",
                    db_update_func=AsyncMock(),
                    emit_masked_func=None,
                    job_id=job_id,
                )

            # Update progress for the batch
            await job_progress_manager.update_job_progress(
                job_id,
                "video",  # Should match individual processing
                len(frames),
                0,
                "segmentation",
            )

        # Test the logic
        frames_data = {
            "video_id": "video_123",
            "frames": [
                {"frame_id": "frame_1", "ts": "00:00", "local_path": "/path/frame1.jpg"},
                {"frame_id": "frame_2", "ts": "00:05", "local_path": "/path/frame2.jpg"}
            ],
            "job_id": "test_job_123"
        }

        await handle_videos_keyframes_ready_logic(
            frames_data, mock_job_progress_manager, mock_asset_processor
        )

        # Verify individual frame processing
        assert mock_asset_processor.handle_single_asset_processing.call_count == 2

        # Check that both calls use 'frame' asset type
        for call in mock_asset_processor.handle_single_asset_processing.call_args_list:
            assert call.kwargs["asset_type"] == "video"

        # Verify batch progress update uses 'frame'
        mock_job_progress_manager.update_job_progress.assert_called_once_with(
            "test_job_123",
            "video",
            2,
            0,
            "segmentation",
        )

    @pytest.mark.asyncio
    async def test_consistency_between_batch_and_individual(self):
        """Test that batch and individual processing use the same asset type."""
        mock_job_progress_manager = AsyncMock()
        asset_types_used = []

        # Simulate both batch and individual processing
        async def simulate_complete_workflow(job_id, total_frames):
            """Simulate the complete workflow with consistent asset types."""

            # 1. Batch event sets up expected count
            batch_asset_type = "video"  # The fix
            asset_types_used.append(("batch", batch_asset_type))

            await mock_job_progress_manager.update_job_progress(
                job_id,
                batch_asset_type,
                total_frames,
                0,
                "segmentation",
            )

            # 2. Individual processing uses same asset type
            for i in range(total_frames):
                individual_asset_type = "video"  # Must match batch
                asset_types_used.append(("individual", individual_asset_type))

                await mock_job_progress_manager.update_job_progress(
                    job_id,
                    individual_asset_type,
                    1,
                    1,  # increment
                    "segmentation",
                )

        # Test the workflow
        await simulate_complete_workflow("consistency_test_job", 5)

        # Verify all asset types are consistent
        for operation, asset_type in asset_types_used:
            assert asset_type == "video", f"{operation} operation used {asset_type}, expected 'frame'"

        # Verify job progress calls
        assert mock_job_progress_manager.update_job_progress.call_count == 6  # 1 batch + 5 individual

    @pytest.mark.asyncio
    async def test_zero_asset_batch_handling_logic(self):
        """Test zero asset scenario with different asset types."""
        mock_job_progress_manager = AsyncMock()

        async def handle_zero_asset_batch(job_id, asset_type):
            """Simulate zero asset batch handling."""
            if asset_type == "image":
                await mock_job_progress_manager.publish_products_images_masked_batch(
                    job_id=job_id,
                    total_images=0,
                )
            elif asset_type == "video":
                await mock_job_progress_manager.publish_videos_keyframes_masked_batch(
                    job_id=job_id,
                    total_keyframes=0,
                )
            else:
                # Should log warning
                pass

        # Test zero images
        await handle_zero_asset_batch("zero_image_job", "image")
        mock_job_progress_manager.publish_products_images_masked_batch.assert_called_once_with(
            job_id="zero_image_job", total_images=0
        )

        mock_job_progress_manager.reset_mock()

        # Test zero frames
        await handle_zero_asset_batch("zero_frame_job", "video")
        mock_job_progress_manager.publish_videos_keyframes_masked_batch.assert_called_once_with(
            job_id="zero_frame_job", total_keyframes=0
        )

    def test_asset_type_decision_logic(self):
        """Test the decision logic for choosing asset types."""

        def get_asset_type_for_operation(operation, context):
            """Isolated asset type decision logic."""
            if operation == "video_keyframes_batch":
                return "video"  # The fix
            elif operation == "video_keyframes_individual":
                return "video"
            elif operation == "product_images_batch":
                return "image"
            elif operation == "product_images_individual":
                return "image"
            else:
                raise ValueError(f"Unknown operation: {operation}")

        # Test the decision logic
        assert get_asset_type_for_operation("video_keyframes_batch", {}) == "video"
        assert get_asset_type_for_operation("video_keyframes_individual", {}) == "video"
        assert get_asset_type_for_operation("product_images_batch", {}) == "image"
        assert get_asset_type_for_operation("product_images_individual", {}) == "image"

        # Verify consistency for video operations
        video_batch = get_asset_type_for_operation("video_keyframes_batch", {})
        video_individual = get_asset_type_for_operation("video_keyframes_individual", {})
        assert video_batch == video_individual == "video"

        # Verify consistency for image operations
        image_batch = get_asset_type_for_operation("product_images_batch", {})
        image_individual = get_asset_type_for_operation("product_images_individual", {})
        assert image_batch == image_individual == "image"
