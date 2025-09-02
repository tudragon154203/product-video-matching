"""Image processing operations for product segmentation.

This module handles the core image segmentation operations, including:
- Loading and preprocessing images
- Applying segmentation models to generate masks
- Saving mask files to the filesystem
- Error handling for image processing failures

It serves as a specialized component that focuses solely on the image processing
aspect of product segmentation, delegating file management and database operations
to other modules.
"""
import time
from typing import Optional
from common_py.logging_config import configure_logging
from segmentation.interface import SegmentationInterface

logger = configure_logging("product-segmentor:image_processor")

class ImageProcessor:
    """Handles core image segmentation operations.
    
    This class focuses solely on the image processing aspect of product segmentation,
    applying segmentation models and generating masks while delegating file management
    and database operations to other modules.
    """
    def __init__(self, segmentor: SegmentationInterface):
        """Initialize image processor with segmentation engine.
        
        Args:
            segmentor: Segmentation interface for mask generation
        """
        self.segmentor = segmentor

    async def process_image(
        self,
        image_id: str,
        local_path: str,
        image_type: str,
        file_manager  # FileManager dependency will be injected
    ) -> Optional[str]:
        """Process a single image to generate mask.
        
        This method handles the complete image segmentation pipeline:
        1. Applies segmentation model to extract product region
        2. Measures and logs segmentation performance
        3. Saves generated mask to filesystem via FileManager
        4. Handles errors gracefully
        
        Args:
            image_id: Unique identifier for the image
            local_path: Path to the source image file
            image_type: Type of image ("product" or "frame")
            file_manager: FileManager instance for mask storage
            
        Returns:
            Path to generated mask file or None if processing failed
        """
        try:
            # Start timing for segmentation
            start_time = time.perf_counter()
            
            # Generate mask using segmentation model
            mask = await self.segmentor.segment_image(local_path)
            
            # Calculate segmentation time
            segmentation_time = time.perf_counter() - start_time
            
            if mask is None:
                logger.warning("Segmentation failed", image_id=image_id, path=local_path)
                return None
            
            # Log segmentation time
            logger.info(
                "Image segmented",
                segmentation_time_seconds=f"{segmentation_time:.2f}",
                local_path=local_path
            )            
                        # Save mask to filesystem
            if image_type == "product":
                mask_path = await file_manager.save_product_mask(image_id, mask)
            else:  # frame
                mask_path = await file_manager.save_frame_mask(image_id, mask)
            
            return mask_path
            
        except Exception as e:
            logger.error("Error processing image", image_id=image_id, error=str(e))
            return None
