import numpy as np
import pytest
from unittest.mock import Mock, AsyncMock
from services.image_masking_processor import ImageMaskingProcessor


class TestImageMaskingProcessorShapeFix:
    """Test the mask shape mismatch fix in ImageMaskingProcessor."""

    @pytest.fixture
    def mock_processor(self):
        """Create a mock ImageMaskingProcessor for testing."""
        foreground_segmentor = Mock()
        people_segmentor = Mock()
        file_manager = AsyncMock()
        image_processor = AsyncMock()

        processor = ImageMaskingProcessor(
            foreground_segmentor=foreground_segmentor,
            people_segmentor=people_segmentor,
            file_manager=file_manager,
            image_processor=image_processor
        )
        return processor

    @pytest.mark.asyncio
    async def test_subtract_people_mask_shape_compatibility(self, mock_processor):
        """Test that people mask with 3D shape (H, W, 1) is properly handled."""
        # Create test masks with different shapes
        foreground_mask = np.ones((400, 400), dtype=np.uint8) * 255  # 2D mask
        people_mask_3d = np.ones((400, 400, 1), dtype=np.uint8) * 128  # 3D mask with single channel

        # Test the _subtract_people_mask method
        result = await mock_processor._subtract_people_mask(
            foreground_mask=foreground_mask,
            people_mask=people_mask_3d,
            image_id="test_image",
            job_id="test_job"
        )

        # Verify the result has the correct shape
        assert result.shape == (400, 400), f"Expected (400, 400), got {result.shape}"

        # Verify the result is not the same as the original (people mask was subtracted)
        # In the areas where people_mask is 128, we expect the foreground to be reduced
        assert not np.array_equal(result, foreground_mask), "Expected some change after mask subtraction"

    @pytest.mark.asyncio
    async def test_subtract_people_mask_already_2d(self, mock_processor):
        """Test that people mask already in 2D shape works correctly."""
        # Create test masks with same 2D shapes
        foreground_mask = np.ones((400, 400), dtype=np.uint8) * 255
        people_mask_2d = np.ones((400, 400), dtype=np.uint8) * 128

        # Test the _subtract_people_mask method
        result = await mock_processor._subtract_people_mask(
            foreground_mask=foreground_mask,
            people_mask=people_mask_2d,
            image_id="test_image",
            job_id="test_job"
        )

        # Verify the result has the correct shape
        assert result.shape == (400, 400), f"Expected (400, 400), got {result.shape}"

        # Verify the result is not the same as the original
        assert not np.array_equal(result, foreground_mask), "Expected some change after mask subtraction"

    @pytest.mark.asyncio
    async def test_subtract_people_mask_none_people_mask(self, mock_processor):
        """Test that None people mask is handled correctly."""
        foreground_mask = np.ones((400, 400), dtype=np.uint8) * 255

        # Test with None people mask
        result = await mock_processor._subtract_people_mask(
            foreground_mask=foreground_mask,
            people_mask=None,
            image_id="test_image",
            job_id="test_job"
        )

        # Should return the original foreground mask unchanged
        np.testing.assert_array_equal(result, foreground_mask)

    @pytest.mark.asyncio
    async def test_subtract_people_mask_shape_mismatch_warning(self, mock_processor):
        """Test that mismatched shapes still generate warning but don't crash."""
        foreground_mask = np.ones((400, 400), dtype=np.uint8) * 255
        people_mask_wrong_shape = np.ones((300, 300), dtype=np.uint8) * 128  # Different shape

        # Test with mismatched shapes
        result = await mock_processor._subtract_people_mask(
            foreground_mask=foreground_mask,
            people_mask=people_mask_wrong_shape,
            image_id="test_image",
            job_id="test_job"
        )

        # Should return the original foreground mask unchanged due to shape mismatch
        np.testing.assert_array_equal(result, foreground_mask)
