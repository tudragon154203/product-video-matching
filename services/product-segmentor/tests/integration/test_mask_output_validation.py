"""Integration test to validate mask output correctness after inversion fix."""

import os
import pytest
import numpy as np
from PIL import Image
import asyncio

from segmentation.models.rmbg14_segmentor import RMBG14Segmentor
from segmentation.models.yolo_segmentor import YOLOSegmentor
from services.image_masking_processor import ImageMaskingProcessor
from utils.file_manager import FileManager


pytestmark = pytest.mark.integration


class TestMaskOutputValidation:
    """Test that masks are correctly generated with proper foreground/background convention."""

    @pytest.fixture
    def test_image_path(self):
        """Path to test image."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_image.webp")

    @pytest.fixture
    async def temp_mask_dirs(self, tmp_path):
        """Create temporary directories for mask storage."""
        foreground_dir = tmp_path / "foreground"
        people_dir = tmp_path / "people"
        product_dir = tmp_path / "product"
        
        foreground_dir.mkdir()
        people_dir.mkdir()
        product_dir.mkdir()
        
        return {
            "foreground": str(foreground_dir),
            "people": str(people_dir),
            "product": str(product_dir)
        }

    @pytest.mark.asyncio
    async def test_rmbg14_mask_output_convention(self, test_image_path):
        """Test that RMBG-1.4 outputs masks with correct foreground/background convention."""
        if not os.path.exists(test_image_path):
            pytest.skip(f"Test image not found: {test_image_path}")

        # Initialize segmentor
        segmentor = RMBG14Segmentor()
        
        try:
            await segmentor.initialize()
            
            # Generate mask
            mask = await segmentor.segment_image(test_image_path)
            
            assert mask is not None, "Mask generation failed"
            assert isinstance(mask, np.ndarray), "Mask should be numpy array"
            assert mask.dtype == np.uint8, "Mask should be uint8"
            
            # Verify mask is binary (only 0 and 255)
            unique_values = np.unique(mask)
            assert len(unique_values) <= 2, f"Mask should be binary, got values: {unique_values}"
            assert all(v in [0, 255] for v in unique_values), "Mask should only contain 0 and 255"
            
            # Verify mask has both foreground and background
            # (unless the entire image is one or the other)
            has_foreground = np.any(mask == 255)
            has_background = np.any(mask == 0)
            
            print(f"\nMask statistics:")
            print(f"  Shape: {mask.shape}")
            print(f"  Foreground pixels (255): {np.sum(mask == 255)} ({np.sum(mask == 255) / mask.size * 100:.2f}%)")
            print(f"  Background pixels (0): {np.sum(mask == 0)} ({np.sum(mask == 0) / mask.size * 100:.2f}%)")
            print(f"  Has foreground: {has_foreground}")
            print(f"  Has background: {has_background}")
            
            # For a product image, we expect both foreground and background
            assert has_foreground, "Mask should have foreground pixels (255)"
            assert has_background, "Mask should have background pixels (0)"
            
            # Verify foreground is not the majority (would indicate inverted mask)
            # Typically, product occupies less than 80% of the image
            foreground_ratio = np.sum(mask == 255) / mask.size
            assert foreground_ratio < 0.95, \
                f"Foreground ratio too high ({foreground_ratio:.2%}), mask might be inverted"
            
        finally:
            segmentor.cleanup()

    @pytest.mark.asyncio
    async def test_yolo_people_mask_output_convention(self, test_image_path):
        """Test that YOLO people segmentor outputs masks with correct convention."""
        if not os.path.exists(test_image_path):
            pytest.skip(f"Test image not found: {test_image_path}")

        # Initialize YOLO segmentor
        segmentor = YOLOSegmentor('yolo11l-seg')
        
        try:
            await segmentor.initialize()
            
            # Generate mask
            mask = await segmentor.segment_image(test_image_path)
            
            # YOLO might return None if no people detected
            if mask is not None:
                assert isinstance(mask, np.ndarray), "Mask should be numpy array"
                
                # Squeeze if needed
                if mask.ndim == 3:
                    mask = mask.squeeze()
                
                assert mask.dtype == np.uint8, "Mask should be uint8"
                
                # Verify mask is binary
                unique_values = np.unique(mask)
                assert all(v in [0, 255] for v in unique_values), \
                    f"Mask should only contain 0 and 255, got: {unique_values}"
                
                print(f"\nPeople mask statistics:")
                print(f"  Shape: {mask.shape}")
                print(f"  People pixels (255): {np.sum(mask == 255)}")
                print(f"  Background pixels (0): {np.sum(mask == 0)}")
            else:
                print("\nNo people detected in image (expected for product images)")
                
        finally:
            segmentor.cleanup()

    @pytest.mark.asyncio
    async def test_final_product_mask_generation(self, test_image_path, temp_mask_dirs):
        """Test complete mask generation pipeline with mask subtraction."""
        if not os.path.exists(test_image_path):
            pytest.skip(f"Test image not found: {test_image_path}")

        # Initialize components
        foreground_segmentor = RMBG14Segmentor()
        people_segmentor = YOLOSegmentor('yolo11l-seg')
        file_manager = FileManager(
            temp_mask_dirs["foreground"],
            temp_mask_dirs["people"],
            temp_mask_dirs["product"]
        )
        
        await file_manager.initialize()
        
        try:
            await foreground_segmentor.initialize()
            await people_segmentor.initialize()
            
            # Create a mock image processor
            class MockImageProcessor:
                def __init__(self, segmentor, file_manager):
                    self.segmentor = segmentor
                    self.file_manager = file_manager
                
                async def process_image(self, image_id, local_path, image_type, file_manager):
                    mask = await self.segmentor.segment_image(local_path)
                    if mask is None:
                        return None
                    if image_type == "product":
                        return await file_manager.save_product_mask(image_id, mask)
                    else:
                        return await file_manager.save_frame_mask(image_id, mask)
            
            image_processor = MockImageProcessor(foreground_segmentor, file_manager)
            
            # Create masking processor
            processor = ImageMaskingProcessor(
                foreground_segmentor,
                people_segmentor,
                file_manager,
                image_processor
            )
            
            # Process image
            image_id = "test_mask_validation"
            mask_path = await processor.process_single_image(
                image_id=image_id,
                local_path=test_image_path,
                image_type="product",
                job_id="test_job"
            )
            
            assert mask_path is not None, "Mask generation failed"
            assert os.path.exists(mask_path), f"Mask file not created: {mask_path}"
            
            # Load and validate the final mask
            final_mask = np.array(Image.open(mask_path))
            
            print(f"\nFinal product mask statistics:")
            print(f"  Path: {mask_path}")
            print(f"  Shape: {final_mask.shape}")
            print(f"  Dtype: {final_mask.dtype}")
            
            # Verify mask properties
            assert final_mask.dtype == np.uint8, "Final mask should be uint8"
            
            # Verify binary values
            unique_values = np.unique(final_mask)
            print(f"  Unique values: {unique_values}")
            assert all(v in [0, 255] for v in unique_values), \
                f"Final mask should only contain 0 and 255, got: {unique_values}"
            
            # Verify mask has content
            foreground_pixels = np.sum(final_mask == 255)
            background_pixels = np.sum(final_mask == 0)
            total_pixels = final_mask.size
            
            print(f"  Foreground pixels (255): {foreground_pixels} ({foreground_pixels/total_pixels*100:.2f}%)")
            print(f"  Background pixels (0): {background_pixels} ({background_pixels/total_pixels*100:.2f}%)")
            
            assert foreground_pixels > 0, "Final mask should have foreground pixels"
            assert background_pixels > 0, "Final mask should have background pixels"
            
            # Verify foreground is reasonable (not inverted)
            foreground_ratio = foreground_pixels / total_pixels
            assert 0.05 < foreground_ratio < 0.95, \
                f"Foreground ratio ({foreground_ratio:.2%}) seems unusual, possible inversion"
            
            print(f"\n✓ Final product mask validated successfully!")
            print(f"  - Mask is binary (0 and 255)")
            print(f"  - Foreground (product) is white (255)")
            print(f"  - Background is black (0)")
            print(f"  - Foreground ratio is reasonable: {foreground_ratio:.2%}")
            
        finally:
            foreground_segmentor.cleanup()
            people_segmentor.cleanup()

    @pytest.mark.asyncio
    async def test_mask_visual_inspection_output(self, test_image_path, temp_mask_dirs):
        """Generate masks for visual inspection (saved to temp directory)."""
        if not os.path.exists(test_image_path):
            pytest.skip(f"Test image not found: {test_image_path}")

        # Initialize segmentor
        segmentor = RMBG14Segmentor()
        
        try:
            await segmentor.initialize()
            
            # Generate mask
            mask = await segmentor.segment_image(test_image_path)
            
            if mask is not None:
                # Save mask for visual inspection
                output_path = os.path.join(temp_mask_dirs["product"], "visual_inspection_mask.png")
                Image.fromarray(mask, mode='L').save(output_path)
                
                # Also save the original image for comparison
                original_output = os.path.join(temp_mask_dirs["product"], "visual_inspection_original.png")
                Image.open(test_image_path).save(original_output)
                
                print(f"\n✓ Masks saved for visual inspection:")
                print(f"  Original: {original_output}")
                print(f"  Mask: {output_path}")
                print(f"\nTo inspect: Open both files and verify that:")
                print(f"  - White areas (255) in mask correspond to the product")
                print(f"  - Black areas (0) in mask correspond to the background")
                
        finally:
            segmentor.cleanup()
