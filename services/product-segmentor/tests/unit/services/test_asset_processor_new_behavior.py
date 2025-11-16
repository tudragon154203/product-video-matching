"""Unit tests for AssetProcessor - Updated behavior for successful-only progress increment."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from services.asset_processor import AssetProcessor


@pytest.mark.unit
class TestAssetProcessorNewBehavior:
    """Test AssetProcessor handles successful-only processing correctly."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_image_masking_processor = MagicMock()
        self.mock_image_masking_processor.process_single_image = AsyncMock()

        self.mock_db_updater = MagicMock()
        self.mock_db_updater.update_product_image_mask = AsyncMock()

        self.mock_event_emitter = MagicMock()
        self.mock_event_emitter.emit_product_image_masked = AsyncMock()

        self.mock_job_progress_manager = MagicMock()
        self.mock_job_progress_manager.update_job_progress = AsyncMock()
        self.mock_job_progress_manager.job_tracking = {}

        self.processor = AssetProcessor(
            image_masking_processor=self.mock_image_masking_processor,
            db_updater=self.mock_db_updater,
            event_emitter=self.mock_event_emitter,
            job_progress_manager=self.mock_job_progress_manager,
        )

    @pytest.mark.asyncio
    async def test_successful_image_processing_increments_progress(self):
        """Test that successful image processing increments progress counter."""
        # Arrange
        job_id = "test-job-123"
        asset_id = "test-image-456"
        mask_path = "/path/to/mask.png"

        self.mock_image_masking_processor.process_single_image.return_value = mask_path
        self.mock_job_progress_manager.job_tracking[f"{job_id}:image:segmentation"] = {
            "done": 1,
            "expected": 10
        }

        event_data = {
            "image_id": asset_id,
            "local_path": "/path/to/image.jpg",
            "job_id": job_id,
        }

        # Act
        result = await self.processor.handle_single_asset_processing(
            event_data=event_data,
            asset_type="image",
            asset_id_key="image_id",
            db_update_func=self.mock_db_updater.update_product_image_mask,
            emit_masked_func=self.mock_event_emitter.emit_product_image_masked,
            job_id=job_id,
        )

        # Assert
        assert result == mask_path
        self.mock_image_masking_processor.process_single_image.assert_called_once()
        self.mock_db_updater.update_product_image_mask.assert_called_once_with(asset_id, mask_path)
        self.mock_event_emitter.emit_product_image_masked.assert_called_once()

        # Verify progress was incremented
        self.mock_job_progress_manager.update_job_progress.assert_called_once_with(
            job_id, "image", 0, 1, event_type_prefix="segmentation"
        )

    @pytest.mark.asyncio
    async def test_failed_image_processing_does_not_increment_progress(self):
        """Test that failed image processing does NOT increment progress counter.

        NEW BEHAVIOR: Only successful items should increment segmentation progress.
        Failed items should not count toward batch completion to ensure accurate batch event counts.
        """
        # Arrange
        job_id = "test-job-123"
        asset_id = "test-image-456"

        # Simulate segmentation failure
        self.mock_image_masking_processor.process_single_image.return_value = None

        event_data = {
            "image_id": asset_id,
            "local_path": "/path/to/image.jpg",
            "job_id": job_id,
        }

        # Act
        result = await self.processor.handle_single_asset_processing(
            event_data=event_data,
            asset_type="image",
            asset_id_key="image_id",
            db_update_func=self.mock_db_updater.update_product_image_mask,
            emit_masked_func=self.mock_event_emitter.emit_product_image_masked,
            job_id=job_id,
        )

        # Assert
        assert result is None
        self.mock_image_masking_processor.process_single_image.assert_called_once()

        # Database and event emission should NOT happen for failed items
        self.mock_db_updater.update_product_image_mask.assert_not_called()
        self.mock_event_emitter.emit_product_image_masked.assert_not_called()

        # CRITICAL: Progress should NOT be incremented for failed items
        self.mock_job_progress_manager.update_job_progress.assert_not_called()

    @pytest.mark.asyncio
    async def test_mixed_success_failure_scenario_image_batch_counts(self):
        """Test that batch completion counts only successful items when some fail."""
        # Arrange
        job_id = "mixed-scenario-job"

        # Scenario: 3 expected items, 2 succeed, 1 fails
        expected_items = 3
        successful_items = ["img_1", "img_2"]
        failed_item = "img_3"

        # Mock successful processing
        self.mock_image_masking_processor.process_single_image.side_effect = [
            "/path/to/mask_1.png",  # img_1 succeeds
            "/path/to/mask_2.png",  # img_2 succeeds
            None,                    # img_3 fails
        ]

        # Set up job tracking to simulate batch progress
        self.mock_job_progress_manager.job_tracking = {
            f"{job_id}:image:segmentation": {
                "done": 0,  # Start with 0 processed
                "expected": expected_items
            }
        }

        # Act - process all items
        results = []
        for i, asset_id in enumerate([*successful_items, failed_item]):
            self.mock_job_progress_manager.job_tracking[f"{job_id}:image:segmentation"]["done"] = i

            event_data = {
                "image_id": asset_id,
                "local_path": f"/path/to/image_{asset_id}.jpg",
                "job_id": job_id,
            }

            result = await self.processor.handle_single_asset_processing(
                event_data=event_data,
                asset_type="image",
                asset_id_key="image_id",
                db_update_func=self.mock_db_updater.update_product_image_mask,
                emit_masked_func=self.mock_event_emitter.emit_product_image_masked,
                job_id=job_id,
            )
            results.append(result)

        # Assert
        # Successful items should return mask paths
        assert results[0] == "/path/to/mask_1.png"
        assert results[1] == "/path/to/mask_2.png"
        # Failed item should return None
        assert results[2] is None

        # Only successful items should have DB updates and events
        assert self.mock_db_updater.update_product_image_mask.call_count == 2
        assert self.mock_event_emitter.emit_product_image_masked.call_count == 2

        # Only successful items should increment progress
        assert self.mock_job_progress_manager.update_job_progress.call_count == 2

        # Verify calls were made with correct parameters
        progress_calls = self.mock_job_progress_manager.update_job_progress.call_args_list
        for call in progress_calls:
            args, kwargs = call
            assert args[0] == job_id  # job_id
            assert args[1] == "image"  # asset_type
            assert args[2] == 0  # total_items (increment)
            assert args[3] == 1  # increment
            assert kwargs["event_type_prefix"] == "segmentation"

    @pytest.mark.asyncio
    async def test_video_frame_processing_without_emit_func(self):
        """Test that video frame processing works without individual emit function."""
        # Arrange
        job_id = "test-job-123"
        frame_id = "test-frame-456"
        mask_path = "/path/to/mask.png"

        self.mock_image_masking_processor.process_single_image.return_value = mask_path
        self.mock_job_progress_manager.job_tracking[f"{job_id}:video:segmentation"] = {
            "done": 1,
            "expected": 10
        }

        event_data = {
            "frame_id": frame_id,
            "local_path": "/path/to/frame.jpg",
            "job_id": job_id,
        }

        # Act
        result = await self.processor.handle_single_asset_processing(
            event_data=event_data,
            asset_type="video",
            asset_id_key="frame_id",
            db_update_func=self.mock_db_updater.update_product_image_mask,
            emit_masked_func=None,  # Video frames don't emit individual events
            job_id=job_id,
        )

        # Assert
        assert result == mask_path
        self.mock_image_masking_processor.process_single_image.assert_called_once()
        self.mock_db_updater.update_product_image_mask.assert_called_once()

        # No individual event should be emitted for video frames
        self.mock_event_emitter.emit_product_image_masked.assert_not_called()

        # Progress should still be incremented for successful processing
        self.mock_job_progress_manager.update_job_progress.assert_called_once_with(
            job_id, "video", 0, 1, event_type_prefix="segmentation"
        )

    @pytest.mark.asyncio
    async def test_failed_video_frame_processing_does_not_increment_progress(self):
        """Test that failed video frame processing does NOT increment progress counter."""
        # Arrange
        job_id = "test-video-job-123"
        frame_id = "test-frame-456"

        # Simulate segmentation failure
        self.mock_image_masking_processor.process_single_image.return_value = None

        event_data = {
            "frame_id": frame_id,
            "local_path": "/path/to/frame.jpg",
            "job_id": job_id,
        }

        # Act
        result = await self.processor.handle_single_asset_processing(
            event_data=event_data,
            asset_type="video",
            asset_id_key="frame_id",
            db_update_func=self.mock_db_updater.update_product_image_mask,
            emit_masked_func=None,  # Video frames don't emit individual events
            job_id=job_id,
        )

        # Assert
        assert result is None
        self.mock_image_masking_processor.process_single_image.assert_called_once()

        # Database update should NOT happen for failed items
        self.mock_db_updater.update_product_image_mask.assert_not_called()

        # Progress should NOT be incremented for failed items
        self.mock_job_progress_manager.update_job_progress.assert_not_called()