"""Tests for RMBG-2.0 segmentation implementation."""

import pytest
import numpy as np
import torch
from unittest.mock import Mock, AsyncMock, patch
from PIL import Image
import tempfile
import os

from segmentation.interface import SegmentationInterface
from segmentation.rmbg20_segmentor import RMBG20Segmentor


class TestRMBG20Segmentor:
    """Test RMBG-2.0 segmentor implementation."""
    
    def test_rmbg20_segmentor_creation(self):
        """Test RMBG-2.0 segmentor creation."""
        segmentor = RMBG20Segmentor()
        assert segmentor.model_name == "briaai/RMBG-2.0"
        assert not segmentor.is_initialized
    
    def test_rmbg20_segmentor_custom_model(self):
        """Test RMBG-2.0 segmentor with custom model name."""
        custom_model = "custom/rmbg-2.0"
        segmentor = RMBG20Segmentor(model_name=custom_model)
        assert segmentor.model_name == custom_model
    
    @pytest.mark.asyncio
    async def test_rmbg20_segmentor_file_not_found(self):
        """Test RMBG-2.0 segmentor with non-existent file."""
        segmentor = RMBG20Segmentor()
        
        # Mock initialization
        segmentor._initialized = True
        
        with pytest.raises(FileNotFoundError):
            await segmentor.segment_image("/nonexistent/path.jpg")
    
    @pytest.mark.asyncio
    async def test_rmbg20_segmentor_not_initialized(self):
        """Test RMBG-2.0 segmentor when not initialized."""
        segmentor = RMBG20Segmentor()
        
        # Create temporary image file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            img = Image.new('RGB', (100, 100), color='red')
            img.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            # Test segmentation without initialization
            mask = await segmentor.segment_image(tmp_path)
            assert mask is None
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_rmbg20_segmentor_real_image_segmentation(self):
        """Test RMBG-2.0 segmentor with a real mock image and verify mask output."""
        segmentor = RMBG20Segmentor()

        # Create a dummy image file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            img = Image.new('RGB', (224, 224), color='red') # Use a common input size
            img.save(tmp.name)
            tmp_path = tmp.name

        try:
            # Mock the model and processor to avoid actual loading and computation
            with patch('transformers.AutoModelForImageSegmentation.from_pretrained') as mock_model_loader, \
                patch('transformers.AutoImageProcessor.from_pretrained') as mock_processor_loader:
                
                mock_model = Mock()
                mock_processor = Mock()

                mock_model_loader.return_value = mock_model
                mock_processor_loader.return_value = mock_processor

                # Mock the model's forward pass to return a dummy mask output
                # The output should be a tensor that, when processed, becomes a binary mask
                # For a 224x224 image, the output mask will also be 224x224
                mock_model.return_value = Mock(logits=torch.randn(1, 1, 224, 224)) # Simulate logits output

                # Mock the processor's __call__ method to return dummy pixel values
                mock_processor.return_value = {'pixel_values': torch.randn(1, 3, 224, 224)}

                await segmentor.initialize()
                mask = await segmentor.segment_image(tmp_path)

                assert mask is not None
                assert isinstance(mask, Image.Image)
                assert mask.mode == 'L' # Mask should be grayscale
                assert mask.size == (224, 224)

                # Verify that the mask contains only 0s and 255s (binary)
                mask_array = np.array(mask)
                assert np.all(np.isin(mask_array, [0, 255]))

        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__])