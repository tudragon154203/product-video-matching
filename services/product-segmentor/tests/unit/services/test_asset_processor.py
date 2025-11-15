"""Unit tests for AssetProcessor."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from services.asset_processor import AssetProcessor


@pytest.mark.unit
class TestAssetProcessor:
    """Test AssetProcessor handles both successful and failed processing."""

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
    async def test_failed_image_processing_still_increments_progress(self):
        """Test that failed image processing still increments progress counter.
        
        This is critical to prevent jobs from getting stuck when some images fail.
        The job should complete when all items have been attempted, regardless of success/failure.
        """
        # Arrange
        job_id = "test-job-123"
        asset_id = "test-image-456"
        
        # Simulate segmentation failure
        self.mock_image_masking_processor.process_single_image.return_value = None
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
        assert result is None
        self.mock_image_masking_processor.process_single_image.assert_called_once()
        
        # Database and event emission should NOT happen for failed items
        self.mock_db_updater.update_product_image_mask.assert_not_called()
        self.mock_event_emitter.emit_product_image_masked.assert_not_called()
        
        # CRITICAL: Progress should still be incremented even for failed items
        self.mock_job_progress_manager.update_job_progress.assert_called_once_with(
            job_id, "image", 0, 1, event_type_prefix="segmentation"
        )

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
        
        # Progress should still be incremented
        self.mock_job_progress_manager.update_job_progress.assert_called_once()
