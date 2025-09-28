"""Tests for segmentation interface and implementations."""

import pytest
pytestmark = pytest.mark.unit
import numpy as np
from unittest.mock import Mock, AsyncMock, patch
from PIL import Image
import tempfile
import os

from segmentation.interface import SegmentationInterface
from segmentation.models.rmbg20_segmentor import RMBG20Segmentor


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
        # Use the provided test image
        test_image_path = os.path.join(os.path.dirname(__file__), 'test_image.webp')
        
        # Create a temporary copy of the image to simulate a file being passed
        with tempfile.NamedTemporaryFile(suffix='.webp', delete=False) as tmp:
            with Image.open(test_image_path) as img:
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


class TestRMBG20Segmentor:
    """Test RMBG-2.0 segmentor implementation."""
    
    def test_rmbg_segmentor_creation(self):
        """Test RMBG segmentor creation."""
        segmentor = RMBG20Segmentor()
        assert segmentor.model_name == "briaai/RMBG-2.0"
        assert not segmentor.is_initialized
    
    
    
    @pytest.mark.asyncio
    async def test_rmbg_segmentor_file_not_found(self):
        """Test RMBG segmentor with non-existent file."""
        segmentor = RMBG20Segmentor()
        
        # Mock initialization
        segmentor._initialized = True
        
        with pytest.raises(FileNotFoundError):
            await segmentor.segment_image("/nonexistent/path.jpg")
    
    @pytest.mark.asyncio
    async def test_rmbg_segmentor_not_initialized(self):
        """Test RMBG segmentor when not initialized."""
        segmentor = RMBG20Segmentor()
        
        # Create temporary image file
        # Use the provided test image
        test_image_path = os.path.join(os.path.dirname(__file__), 'test_image.webp')
        
        # Create a temporary copy of the image to simulate a file being passed
        with tempfile.NamedTemporaryFile(suffix='.webp', delete=False) as tmp:
            with Image.open(test_image_path) as img:
                img.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            # Test segmentation without initialization
            mask = await segmentor.segment_image(tmp_path)
            assert mask is None
        finally:
            os.unlink(tmp_path)


class TestSegmentorFactory:
    """Test segmentor factory with both RMBG versions."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("model_name,expected_class", [
        ("briaai/RMBG-2.0", "RMBG20Segmentor"),
        ("briaai/RMBG-1.4", "RMBG14Segmentor"),
        ("BriaAI/RMBG-2.0", "RMBG20Segmentor"),
        ("BriaAI/RMBG-1.4", "RMBG14Segmentor"),
        ("rmbg-2.0", "RMBG20Segmentor"),
        ("rmbg-1.4", "RMBG14Segmentor"),
        ("unknown/model", "RMBG20Segmentor"),  # Should default to RMBG-2.0
    ])
    async def test_factory_model_selection(self, model_name, expected_class):
        """Test factory creates correct segmentor based on model name."""
        from services.foreground_segmentor_factory import create_segmentor
        
        segmentor = create_segmentor(model_name)
        
        if expected_class == "RMBG20Segmentor":
            from segmentation.models.rmbg20_segmentor import RMBG20Segmentor
            assert isinstance(segmentor, RMBG20Segmentor)
        elif expected_class == "RMBG14Segmentor":
            from segmentation.models.rmbg14_segmentor import RMBG14Segmentor
            assert isinstance(segmentor, RMBG14Segmentor)
        
        # Verify the model name is set correctly
        if expected_class == "RMBG20Segmentor":
            assert segmentor.model_name == "briaai/RMBG-2.0"
        elif expected_class == "RMBG14Segmentor":
            assert segmentor.model_name == "briaai/RMBG-1.4"
    
    @pytest.mark.asyncio
    async def test_factory_uses_config_default(self):
        """Test that factory uses config default when no model name provided."""
        from services.foreground_segmentor_factory import create_segmentor
        from config_loader import config
        
        # Mock the config to use RMBG-2.0
        original_model = config.FOREGROUND_SEG_MODEL_NAME
        config.FOREGROUND_SEG_MODEL_NAME = "briaai/RMBG-2.0"
        
        try:
            segmentor = create_segmentor()  # No model name provided
            from segmentation.models.rmbg20_segmentor import RMBG20Segmentor
            assert isinstance(segmentor, RMBG20Segmentor)
            assert segmentor.model_name == "briaai/RMBG-2.0"
        finally:
            # Restore original config
            config.FOREGROUND_SEG_MODEL_NAME = original_model
    
    @pytest.mark.asyncio
    async def test_factory_config_rmbg14_default(self):
        """Test that factory creates RMBG-1.4 when config uses RMBG-1.4."""
        from services.foreground_segmentor_factory import create_segmentor
        from config_loader import config
        
        # Mock the config to use RMBG-1.4
        original_model = config.FOREGROUND_SEG_MODEL_NAME
        config.FOREGROUND_SEG_MODEL_NAME = "briaai/RMBG-1.4"
        
        try:
            segmentor = create_segmentor()  # No model name provided
            from segmentation.models.rmbg14_segmentor import RMBG14Segmentor
            assert isinstance(segmentor, RMBG14Segmentor)
            assert segmentor.model_name == "briaai/RMBG-1.4"
        finally:
            # Restore original config
            config.FOREGROUND_SEG_MODEL_NAME = original_model

