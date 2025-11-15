"""Integration test to generate and save all mask types for debugging."""

import os
import pytest
import numpy as np
from PIL import Image
import cv2

from segmentation.models.rmbg14_segmentor import RMBG14Segmentor
from segmentation.models.rmbg20_segmentor import RMBG20Segmentor
from segmentation.models.yolo_segmentor import YOLOSegmentor


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.parametrize("model_version,segmentor_class,model_name", [
    ("14", RMBG14Segmentor, "RMBG-1.4"),
    ("20", RMBG20Segmentor, "RMBG-2.0"),
])
async def test_generate_all_masks_for_debugging(model_version, segmentor_class, model_name):
    """
    Generate and save all three mask types for visual debugging:
    1. Foreground mask (from RMBG)
    2. People mask (from YOLO)
    3. Final product mask (foreground - people)
    """
    # Get test image path
    test_image_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "test_image.webp"
    )
    
    if not os.path.exists(test_image_path):
        pytest.skip(f"Test image not found: {test_image_path}")
    
    output_dir = os.path.dirname(test_image_path)
    
    print(f"\n{'='*70}")
    print(f"🔍 MASK GENERATION DEBUG TEST - {model_name}")
    print(f"{'='*70}")
    print(f"📷 Test image: {test_image_path}")
    print(f"💾 Output directory: {output_dir}")
    print(f"🤖 Model version: {model_name}\n")
    
    # Initialize segmentors
    foreground_segmentor = segmentor_class()
    people_segmentor = YOLOSegmentor('yolo11l-seg')
    
    try:
        # Initialize models
        print(f"🔧 Initializing {model_name} (foreground segmentor)...")
        await foreground_segmentor.initialize()
        print(f"✓ {model_name} initialized")
        
        print("🔧 Initializing YOLO11l-seg (people segmentor)...")
        await people_segmentor.initialize()
        print("✓ YOLO11l-seg initialized\n")
        
        # ===== STEP 1: Generate Foreground Mask =====
        print(f"{'─'*70}")
        print(f"STEP 1: Generating Foreground Mask ({model_name})")
        print(f"{'─'*70}")
        
        foreground_mask = await foreground_segmentor.segment_image(test_image_path)
        
        if foreground_mask is None:
            print("❌ Foreground mask generation failed")
            return
        
        # Analyze foreground mask
        fg_white = np.sum(foreground_mask == 255)
        fg_black = np.sum(foreground_mask == 0)
        fg_total = foreground_mask.size
        fg_ratio = fg_white / fg_total
        
        print(f"✓ Foreground mask generated")
        print(f"  Shape: {foreground_mask.shape}")
        print(f"  Unique values: {np.unique(foreground_mask)}")
        print(f"  White pixels (255): {fg_white:,} ({fg_ratio:.2%})")
        print(f"  Black pixels (0): {fg_black:,} ({(1-fg_ratio):.2%})")
        
        # Save foreground mask with version suffix
        fg_output = os.path.join(output_dir, f"test_image_mask_rmbg{model_version}_1_foreground.png")
        Image.fromarray(foreground_mask, mode='L').save(fg_output)
        print(f"  💾 Saved: {os.path.basename(fg_output)}\n")
        
        # ===== STEP 2: Generate People Mask =====
        print(f"{'─'*70}")
        print("STEP 2: Generating People Mask (YOLO)")
        print(f"{'─'*70}")
        
        people_mask = await people_segmentor.segment_image(test_image_path)
        
        if people_mask is not None:
            # Squeeze if 3D
            if people_mask.ndim == 3 and people_mask.shape[2] == 1:
                people_mask = people_mask.squeeze(axis=2)
            
            # Analyze people mask
            ppl_white = np.sum(people_mask == 255)
            ppl_black = np.sum(people_mask == 0)
            ppl_total = people_mask.size
            ppl_ratio = ppl_white / ppl_total
            
            print(f"✓ People mask generated")
            print(f"  Shape: {people_mask.shape}")
            print(f"  Unique values: {np.unique(people_mask)}")
            print(f"  White pixels (255): {ppl_white:,} ({ppl_ratio:.2%})")
            print(f"  Black pixels (0): {ppl_black:,} ({(1-ppl_ratio):.2%})")
            
            # Save people mask with version suffix
            ppl_output = os.path.join(output_dir, f"test_image_mask_rmbg{model_version}_2_people.png")
            Image.fromarray(people_mask, mode='L').save(ppl_output)
            print(f"  💾 Saved: {os.path.basename(ppl_output)}\n")
        else:
            print("ℹ️  No people detected in image")
            print("  People mask is None (expected for product-only images)\n")
            # Create empty people mask for final calculation
            people_mask = np.zeros_like(foreground_mask)
            ppl_output = os.path.join(output_dir, f"test_image_mask_rmbg{model_version}_2_people.png")
            Image.fromarray(people_mask, mode='L').save(ppl_output)
            print(f"  💾 Saved empty mask: {os.path.basename(ppl_output)}\n")
        
        # ===== STEP 3: Generate Final Product Mask =====
        print(f"{'─'*70}")
        print("STEP 3: Generating Final Product Mask (Foreground - People)")
        print(f"{'─'*70}")
        
        # Ensure both masks have same shape
        if foreground_mask.shape != people_mask.shape:
            print(f"⚠️  Shape mismatch!")
            print(f"  Foreground: {foreground_mask.shape}")
            print(f"  People: {people_mask.shape}")
            # Resize people mask to match foreground
            people_mask = cv2.resize(people_mask, 
                                    (foreground_mask.shape[1], foreground_mask.shape[0]), 
                                    interpolation=cv2.INTER_NEAREST)
            print(f"  Resized people mask to: {people_mask.shape}")
        
        # Calculate final mask: foreground AND (NOT people)
        final_mask = cv2.bitwise_and(foreground_mask, cv2.bitwise_not(people_mask))
        
        # Analyze final mask
        final_white = np.sum(final_mask == 255)
        final_black = np.sum(final_mask == 0)
        final_total = final_mask.size
        final_ratio = final_white / final_total
        
        print(f"✓ Final product mask generated")
        print(f"  Shape: {final_mask.shape}")
        print(f"  Unique values: {np.unique(final_mask)}")
        print(f"  White pixels (255): {final_white:,} ({final_ratio:.2%})")
        print(f"  Black pixels (0): {final_black:,} ({(1-final_ratio):.2%})")
        
        # Save final mask with version suffix
        final_output = os.path.join(output_dir, f"test_image_mask_rmbg{model_version}_3_final.png")
        Image.fromarray(final_mask, mode='L').save(final_output)
        print(f"  💾 Saved: {os.path.basename(final_output)}\n")
        
        # ===== Summary =====
        print(f"{'='*70}")
        print(f"📊 SUMMARY - {model_name}")
        print(f"{'='*70}")
        print(f"Original image:    {os.path.basename(test_image_path)}")
        print(f"Foreground mask:   {os.path.basename(fg_output)} ({fg_ratio:.2%} white)")
        print(f"People mask:       {os.path.basename(ppl_output)} ({ppl_ratio if people_mask is not None else 0:.2%} white)")
        print(f"Final mask:        {os.path.basename(final_output)} ({final_ratio:.2%} white)")
        print(f"\n💡 Interpretation:")
        print(f"  - White (255) = Foreground/Product to keep")
        print(f"  - Black (0) = Background to remove")
        print(f"\n✓ All {model_name} masks saved to: {output_dir}")
        print(f"{'='*70}\n")
        
        # Assertions to verify masks are valid
        assert foreground_mask is not None
        assert final_mask is not None
        assert np.all(np.isin(foreground_mask, [0, 255])), "Foreground mask should be binary"
        assert np.all(np.isin(final_mask, [0, 255])), "Final mask should be binary"
        
    finally:
        foreground_segmentor.cleanup()
        people_segmentor.cleanup()


if __name__ == "__main__":
    """Run test directly for quick debugging."""
    import asyncio
    
    asyncio.run(test_generate_all_masks_for_debugging())
