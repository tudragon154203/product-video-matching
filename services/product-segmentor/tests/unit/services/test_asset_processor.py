"""Unit tests for AssetProcessor."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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


@pytest.mark.unit
class TestAssetProcessorOOMRetry:
    """Test OOM retry logic in AssetProcessor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_image_masking_processor = MagicMock()
        self.mock_image_masking_processor.process_single_image = AsyncMock()
        
        self.mock_db_updater = MagicMock()
        self.mock_event_emitter = MagicMock()
        self.mock_job_progress_manager = MagicMock()
        
        self.processor = AssetProcessor(
            image_masking_processor=self.mock_image_masking_processor,
            db_updater=self.mock_db_updater,
            event_emitter=self.mock_event_emitter,
            job_progress_manager=self.mock_job_progress_manager,
        )

    def test_is_oom_error_cuda_out_of_memory(self):
        """Test detection of CUDA out of memory error."""
        error = RuntimeError("CUDA out of memory. Tried to allocate 192 MiB")
        assert self.processor._is_oom_error(error) is True

    def test_is_oom_error_cudnn_alloc_failed(self):
        """Test detection of cuDNN allocation failure."""
        error = RuntimeError("cuDNN error: CUDNN_STATUS_ALLOC_FAILED")
        assert self.processor._is_oom_error(error) is True

    def test_is_oom_error_generic_oom(self):
        """Test detection of generic out of memory error."""
        error = RuntimeError("out of memory during tensor allocation")
        assert self.processor._is_oom_error(error) is True

    def test_is_oom_error_non_oom(self):
        """Test that non-OOM errors are not detected as OOM."""
        error = RuntimeError("File not found")
        assert self.processor._is_oom_error(error) is False

    @pytest.mark.asyncio
    async def test_process_with_retry_success_first_attempt(self):
        """Test successful processing on first attempt without retry."""
        self.mock_image_masking_processor.process_single_image.return_value = "/path/to/mask.png"
        
        with patch("services.asset_processor.config") as mock_config:
            mock_config.RETRY_ON_OOM = True
            mock_config.MAX_OOM_RETRIES = 3
            
            result = await self.processor._process_with_retry(
                asset_id="img-123",
                local_path="/path/to/image.jpg",
                asset_type="image",
                job_id="job-456"
            )
            
            assert result == "/path/to/mask.png"
            assert self.mock_image_masking_processor.process_single_image.call_count == 1

    @pytest.mark.asyncio
    async def test_process_with_retry_oom_then_success(self):
        """Test OOM error followed by successful retry."""
        # First call raises OOM, second succeeds
        self.mock_image_masking_processor.process_single_image.side_effect = [
            RuntimeError("CUDA out of memory. Tried to allocate 192 MiB"),
            "/path/to/mask.png"
        ]
        
        with patch("services.asset_processor.config") as mock_config, \
             patch("services.asset_processor.clear_gpu_memory") as mock_clear, \
             patch("services.asset_processor.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            
            mock_config.RETRY_ON_OOM = True
            mock_config.MAX_OOM_RETRIES = 3
            
            result = await self.processor._process_with_retry(
                asset_id="img-123",
                local_path="/path/to/image.jpg",
                asset_type="image",
                job_id="job-456"
            )
            
            assert result == "/path/to/mask.png"
            assert self.mock_image_masking_processor.process_single_image.call_count == 2
            assert mock_clear.call_count == 1
            assert mock_sleep.call_count == 1
            mock_sleep.assert_called_with(0.5)

    @pytest.mark.asyncio
    async def test_process_with_retry_oom_exhausted(self):
        """Test OOM error persisting after all retries."""
        # All attempts raise OOM
        self.mock_image_masking_processor.process_single_image.side_effect = RuntimeError(
            "CUDA out of memory. Tried to allocate 192 MiB"
        )
        
        with patch("services.asset_processor.config") as mock_config, \
             patch("services.asset_processor.clear_gpu_memory") as mock_clear, \
             patch("services.asset_processor.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            
            mock_config.RETRY_ON_OOM = True
            mock_config.MAX_OOM_RETRIES = 3
            
            result = await self.processor._process_with_retry(
                asset_id="img-123",
                local_path="/path/to/image.jpg",
                asset_type="image",
                job_id="job-456"
            )
            
            assert result is None
            assert self.mock_image_masking_processor.process_single_image.call_count == 4  # Initial + 3 retries
            assert mock_clear.call_count == 3
            assert mock_sleep.call_count == 3

    @pytest.mark.asyncio
    async def test_process_with_retry_non_oom_error(self):
        """Test non-OOM error fails immediately without retry."""
        self.mock_image_masking_processor.process_single_image.side_effect = RuntimeError(
            "File not found"
        )
        
        with patch("services.asset_processor.config") as mock_config, \
             patch("services.asset_processor.clear_gpu_memory") as mock_clear:
            
            mock_config.RETRY_ON_OOM = True
            mock_config.MAX_OOM_RETRIES = 3
            
            result = await self.processor._process_with_retry(
                asset_id="img-123",
                local_path="/path/to/image.jpg",
                asset_type="image",
                job_id="job-456"
            )
            
            assert result is None
            assert self.mock_image_masking_processor.process_single_image.call_count == 1
            mock_clear.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_with_retry_disabled(self):
        """Test retry disabled via config."""
        self.mock_image_masking_processor.process_single_image.side_effect = RuntimeError(
            "CUDA out of memory"
        )
        
        with patch("services.asset_processor.config") as mock_config:
            mock_config.RETRY_ON_OOM = False
            mock_config.MAX_OOM_RETRIES = 0
            
            result = await self.processor._process_with_retry(
                asset_id="img-123",
                local_path="/path/to/image.jpg",
                asset_type="image",
                job_id="job-456"
            )
            
            assert result is None
            assert self.mock_image_masking_processor.process_single_image.call_count == 1

    @pytest.mark.asyncio
    async def test_process_with_retry_exponential_backoff(self):
        """Test exponential backoff delays on retries."""
        # Fail 3 times, then succeed
        self.mock_image_masking_processor.process_single_image.side_effect = [
            RuntimeError("CUDA out of memory"),
            RuntimeError("CUDA out of memory"),
            RuntimeError("CUDA out of memory"),
            "/path/to/mask.png"
        ]
        
        with patch("services.asset_processor.config") as mock_config, \
             patch("services.asset_processor.clear_gpu_memory"), \
             patch("services.asset_processor.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            
            mock_config.RETRY_ON_OOM = True
            mock_config.MAX_OOM_RETRIES = 3
            
            result = await self.processor._process_with_retry(
                asset_id="img-123",
                local_path="/path/to/image.jpg",
                asset_type="image",
                job_id="job-456"
            )
            
            assert result == "/path/to/mask.png"
            # Verify exponential backoff: 0.5s, 1.0s, 2.0s
            assert mock_sleep.call_count == 3
            calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert calls == [0.5, 1.0, 2.0]

