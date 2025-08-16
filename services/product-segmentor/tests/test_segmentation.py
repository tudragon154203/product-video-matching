"""Tests for segmentation interface and implementations."""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock, patch
from PIL import Image
import tempfile
import os

from segmentation.interface import SegmentationInterface
from segmentation.rmbg_segmentor import RMBGSegmentor


class MockSegmentor(SegmentationInterface):
    """Mock segmentor for testing interface."""
    
    def __init__(self):
        self._initialized = False
    
    async def initialize(self) -> None:
        self._initialized = True
    
    async def segment_image(self, image_path: str) -> np.ndarray:
        if not self._initialized:
            return None
        return np.ones((100, 100), dtype=np.uint8) * 255
    
    def cleanup(self) -> None:
        self._initialized = False
    
    @property
    def model_name(self) -> str:
        return "mock"
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized


class TestSegmentationInterface:
    """Test segmentation interface contract."""
    
    @pytest.mark.asyncio
    async def test_mock_segmentor_lifecycle(self):
        """Test segmentor initialization and cleanup."""
        segmentor = MockSegmentor()
        
        # Initially not initialized
        assert not segmentor.is_initialized
        assert segmentor.model_name == "mock"
        
        # Initialize
        await segmentor.initialize()
        assert segmentor.is_initialized
        
        # Cleanup
        segmentor.cleanup()
        assert not segmentor.is_initialized
    
    @pytest.mark.asyncio
    async def test_mock_segmentor_segmentation(self):
        """Test segmentation functionality."""
        segmentor = MockSegmentor()
        await segmentor.initialize()
        
        # Create temporary image file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Create a simple test image
            img = Image.new('RGB', (100, 100), color='red')
            img.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            # Test segmentation
            mask = await segmentor.segment_image(tmp_path)
            assert mask is not None
            assert mask.shape == (100, 100)
            assert np.all(mask == 255)
        finally:
            # Cleanup
            os.unlink(tmp_path)
            segmentor.cleanup()


class TestRMBGSegmentor:
    """Test RMBG segmentor implementation."""
    
    def test_rmbg_segmentor_creation(self):
        """Test RMBG segmentor creation."""
        segmentor = RMBGSegmentor()
        assert segmentor.model_name == "briaai/RMBG-1.4"
        assert not segmentor.is_initialized
    
    def test_rmbg_segmentor_custom_model(self):
        """Test RMBG segmentor with custom model name."""
        custom_model = "custom/model"
        segmentor = RMBGSegmentor(model_name=custom_model)
        assert segmentor.model_name == custom_model
    
    @pytest.mark.asyncio
    async def test_rmbg_segmentor_file_not_found(self):
        """Test RMBG segmentor with non-existent file."""
        segmentor = RMBGSegmentor()
        
        # Mock initialization
        segmentor._initialized = True
        
        with pytest.raises(FileNotFoundError):
            await segmentor.segment_image("/nonexistent/path.jpg")
    
    @pytest.mark.asyncio
    async def test_rmbg_segmentor_not_initialized(self):
        """Test RMBG segmentor when not initialized."""
        segmentor = RMBGSegmentor()
        
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


if __name__ == "__main__":
    pytest.main([__file__])