"""Image processing for segmentation."""
import time
from typing import Optional
from common_py.logging_config import configure_logging
from segmentation.interface import SegmentationInterface

logger = configure_logging("product-segmentor")

class ImageProcessor:
    def __init__(self, segmentor: SegmentationInterface):
        self.segmentor = segmentor

    async def process_image(
        self, 
        image_id: str, 
        local_path: str, 
        image_type: str,
        file_manager  # FileManager dependency will be injected
    ) -> Optional[str]:
        """Process a single image to generate mask.
        
        Args:
            image_id: Unique identifier for the image
            local_path: Path to the source image
            image_type: Type of image ("product" or "frame")
            
        Returns:
            Path to generated mask or None if processing failed
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
            logger.info("Image segmented", image_id=image_id, image_type=image_type,
                      segmentation_time_seconds=segmentation_time, local_path=local_path)
            
            # Save mask to filesystem
            if image_type == "product":
                mask_path = await file_manager.save_product_mask(image_id, mask)
            else:  # frame
                mask_path = await file_manager.save_frame_mask(image_id, mask)
            
            return mask_path
            
        except Exception as e:
            logger.error("Error processing image", image_id=image_id, error=str(e))
            return None