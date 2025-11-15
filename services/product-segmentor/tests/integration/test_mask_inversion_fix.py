"""Quick integration test to verify mask inversion fix is working."""

import os
import pytest
import numpy as np
from PIL import Image

from segmentation.models.rmbg14_segmentor import RMBG14Segmentor


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_rmbg_mask_not_inverted():
    """
    Test that RMBG model outputs masks with correct convention after inversion fix.
    
    This test verifies that:
    1. Foreground (product) pixels are WHITE (255)
    2. Background pixels are BLACK (0)
    3. The mask is not inverted
    """
    # Get test image path
    test_image_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "test_image.webp"
    )
    
    if not os.path.exists(test_image_path):
        pytest.skip(f"Test image not found: {test_image_path}")
    
    # Initialize segmentor
    segmentor = RMBG14Segmentor()
    
    try:
        await segmentor.initialize()
        
        # Generate mask
        mask = await segmentor.segment_image(test_image_path)
        
        # Assertions
        assert mask is not None, "Mask generation failed"
        assert isinstance(mask, np.ndarray), "Mask should be numpy array"
        assert mask.dtype == np.uint8, "Mask should be uint8"
        
        # Check mask is binary (only 0 and 255)
        unique_values = np.unique(mask)
        assert len(unique_values) <= 2, f"Mask should be binary, got: {unique_values}"
        assert all(v in [0, 255] for v in unique_values), \
            f"Mask should only contain 0 and 255, got: {unique_values}"
        
        # Calculate foreground/background ratios
        foreground_pixels = np.sum(mask == 255)
        background_pixels = np.sum(mask == 0)
        total_pixels = mask.size
        foreground_ratio = foreground_pixels / total_pixels
        
        # Verify we have both foreground and background
        assert foreground_pixels > 0, "Mask should have foreground pixels (255)"
        assert background_pixels > 0, "Mask should have background pixels (0)"
        
        # Print statistics for analysis
        print(f"\n✓ Mask statistics:")
        print(f"  Foreground (255) pixels: {foreground_pixels} ({foreground_ratio:.2%})")
        print(f"  Background (0) pixels: {background_pixels} ({(1-foreground_ratio):.2%})")
        
        # Key test: Verify mask is NOT inverted
        # If foreground is > 90%, the mask is likely inverted (background detected as foreground)
        # If foreground is < 5%, either the mask is inverted OR detection failed
        
        if foreground_ratio > 0.90:
            raise AssertionError(
                f"Foreground ratio is {foreground_ratio:.2%}, mask appears to be INVERTED! "
                f"Expected product (white/255) to occupy less than 90% of image."
            )
        
        if foreground_ratio < 0.02:
            # Very small foreground - could be inverted or poor detection
            # Check if inverting would give a more reasonable ratio
            inverted_ratio = 1 - foreground_ratio
            if 0.05 < inverted_ratio < 0.90:
                raise AssertionError(
                    f"Foreground ratio is only {foreground_ratio:.2%}. "
                    f"If inverted, it would be {inverted_ratio:.2%}, which seems more reasonable. "
                    f"Mask may still be INVERTED!"
                )
            else:
                print(f"  ⚠ Warning: Very small foreground ({foreground_ratio:.2%}), but inversion doesn't help either.")
                print(f"  This might be expected for this particular test image.")
        
        print(f"  ✓ Mask convention: 255=foreground, 0=background")
        print(f"  ✓ Mask is properly binarized")
        
    finally:
        segmentor.cleanup()


@pytest.mark.asyncio
async def test_mask_values_are_binary():
    """Test that mask contains only binary values (0 and 255)."""
    test_image_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "test_image.webp"
    )
    
    if not os.path.exists(test_image_path):
        pytest.skip(f"Test image not found: {test_image_path}")
    
    segmentor = RMBG14Segmentor()
    
    try:
        await segmentor.initialize()
        mask = await segmentor.segment_image(test_image_path)
        
        assert mask is not None
        
        # Verify only 0 and 255 values exist
        unique_values = np.unique(mask)
        assert set(unique_values).issubset({0, 255}), \
            f"Mask should only contain 0 and 255, found: {unique_values}"
        
        print(f"\n✓ Mask is properly binarized to 0 and 255")
        
    finally:
        segmentor.cleanup()


if __name__ == "__main__":
    """Run tests directly for quick validation."""
    import asyncio
    
    print("Running mask inversion fix validation...\n")
    
    async def run_tests():
        await test_rmbg_mask_not_inverted()
        await test_mask_values_are_binary()
    
    asyncio.run(run_tests())
    print("\n✓ All tests passed!")
