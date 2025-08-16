"""Tests for file manager functionality."""

import pytest
import numpy as np
import tempfile
import shutil
from pathlib import Path
from PIL import Image

from file_manager import FileManager


class TestFileManager:
    """Test file manager operations."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def file_manager(self, temp_dir):
        """Create file manager with temporary directory."""
        return FileManager(base_path=temp_dir)
    
    @pytest.mark.asyncio
    async def test_initialize_creates_directories(self, file_manager, temp_dir):
        """Test that initialization creates required directories."""
        await file_manager.initialize()
        
        base_path = Path(temp_dir)
        assert (base_path / "products").exists()
        assert (base_path / "frames").exists()
    
    @pytest.mark.asyncio
    async def test_save_product_mask(self, file_manager, temp_dir):
        """Test saving product mask."""
        await file_manager.initialize()
        
        # Create test mask
        mask = np.ones((100, 100), dtype=np.uint8) * 255
        image_id = "test_image_123"
        
        # Save mask
        mask_path = await file_manager.save_product_mask(image_id, mask)
        
        # Verify file exists
        assert Path(mask_path).exists()
        assert mask_path.endswith(f"{image_id}.png")
        assert "products" in mask_path
        
        # Verify mask content
        saved_mask = np.array(Image.open(mask_path))
        assert saved_mask.shape == (100, 100)
        assert np.all(saved_mask == 255)
    
    @pytest.mark.asyncio
    async def test_save_frame_mask(self, file_manager, temp_dir):
        """Test saving frame mask."""
        await file_manager.initialize()
        
        # Create test mask
        mask = np.zeros((50, 75), dtype=np.uint8)
        frame_id = "test_frame_456"
        
        # Save mask
        mask_path = await file_manager.save_frame_mask(frame_id, mask)
        
        # Verify file exists
        assert Path(mask_path).exists()
        assert mask_path.endswith(f"{frame_id}.png")
        assert "frames" in mask_path
        
        # Verify mask content
        saved_mask = np.array(Image.open(mask_path))
        assert saved_mask.shape == (50, 75)
        assert np.all(saved_mask == 0)
    
    @pytest.mark.asyncio
    async def test_mask_normalization(self, file_manager):
        """Test that masks are normalized to 0/255 values."""
        await file_manager.initialize()
        
        # Create mask with various values
        mask = np.array([
            [0, 50, 100],
            [127, 128, 200],
            [255, 300, 1000]  # Values > 255 should be clipped
        ], dtype=np.uint16)
        
        mask_path = await file_manager.save_product_mask("test_norm", mask)
        
        # Load and verify normalization
        saved_mask = np.array(Image.open(mask_path))
        expected = np.array([
            [0, 0, 0],
            [0, 255, 255],
            [255, 255, 255]
        ], dtype=np.uint8)
        
        np.testing.assert_array_equal(saved_mask, expected)
    
    @pytest.mark.asyncio
    async def test_mask_exists(self, file_manager):
        """Test mask existence checking."""
        await file_manager.initialize()
        
        # Non-existent mask
        assert not await file_manager.mask_exists("/nonexistent/path.png")
        
        # Create and save a mask
        mask = np.ones((10, 10), dtype=np.uint8) * 255
        mask_path = await file_manager.save_product_mask("exists_test", mask)
        
        # Should exist now
        assert await file_manager.mask_exists(mask_path)
    
    @pytest.mark.asyncio
    async def test_get_mask_size(self, file_manager):
        """Test getting mask dimensions."""
        await file_manager.initialize()
        
        # Non-existent file
        size = await file_manager.get_mask_size("/nonexistent/path.png")
        assert size is None
        
        # Create mask with specific size
        mask = np.ones((80, 120), dtype=np.uint8) * 255
        mask_path = await file_manager.save_product_mask("size_test", mask)
        
        # Get size
        size = await file_manager.get_mask_size(mask_path)
        assert size == (120, 80)  # PIL returns (width, height)
    
    def test_get_expected_paths(self, file_manager):
        """Test getting expected mask paths."""
        # Product mask path
        product_path = file_manager.get_product_mask_path("img_123")
        assert product_path.endswith("products/img_123.png")
        
        # Frame mask path
        frame_path = file_manager.get_frame_mask_path("frame_456")
        assert frame_path.endswith("frames/frame_456.png")
    
    @pytest.mark.asyncio
    async def test_atomic_save_on_error(self, file_manager, temp_dir):
        """Test that failed saves don't leave partial files."""
        await file_manager.initialize()
        
        # Create invalid mask that will cause save to fail
        invalid_mask = "not_an_array"
        
        with pytest.raises(Exception):
            await file_manager.save_product_mask("error_test", invalid_mask)
        
        # Verify no partial files left behind
        products_dir = Path(temp_dir) / "products"
        files = list(products_dir.glob("error_test*"))
        assert len(files) == 0


if __name__ == "__main__":
    pytest.main([__file__])