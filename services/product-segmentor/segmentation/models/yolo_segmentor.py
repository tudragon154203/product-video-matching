from ultralytics import YOLO
import numpy as np
import cv2
import os
from typing import Optional

from segmentation.base_segmentation import BaseSegmentation
from config_loader import config
from common_py.logging_config import configure_logging

logger = configure_logging("yolo-segmentor")

class YOLOSegmentor(BaseSegmentation):
    """YOLOv8 segmentation model for people segmentation."""

    def __init__(self, model_name: str = 'yolo11l-seg.pt'):
        super().__init__()
        self._model_path = os.path.join(config.PEOPLE_SEG_MODEL_CACHE, model_name)
        self._model: Optional[YOLO] = None
        # Set the YOLO_MODEL_DIR environment variable for ultralytics library
        os.environ['YOLO_MODEL_DIR'] = config.PEOPLE_SEG_MODEL_CACHE

    async def initialize(self) -> None:
        """Initialize the YOLO segmentation model."""
        try:
            logger.info("Initializing model",
                       model_name=self.model_name,
                       model_path=self._model_path)
            self._model = YOLO(self._model_path)
            logger.info("Model initialized successfully",
                       model_name=self.model_name)
        except Exception as e:
            logger.error("Model initialization failed",
                        model_name=self.model_name,
                        model_path=self._model_path,
                        error=str(e),
                        error_type=type(e).__name__)
            raise

    async def segment_image(self, image_path: str) -> Optional[np.ndarray]:
        """Generate people mask for image.

        Args:
            image_path: Path to input image file

        Returns:
            Binary mask as numpy array (0=background, 255=foreground)
            or None if segmentation fails
        """
        if not self._initialized:
            raise Exception("YOLO segmentor not initialized. Call initialize() first.")

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        try:
            # Perform inference, filtering for the 'person' class (class ID 0)
            # conf=0.5 is a confidence threshold, adjust as needed
            results = self._model.predict(image_path, classes=0, conf=0.5, verbose=False)

            people_mask = None
            for r in results:
                if r.masks is not None:
                    # Combine all person masks into a single mask
                    combined_mask = np.zeros(r.masks.orig_shape[:2], dtype=np.uint8)
                    for mask_tensor in r.masks.data:
                        mask_np = mask_tensor.cpu().numpy()
                        if mask_np.ndim == 3:
                            mask_np = mask_np.squeeze()

                        resized_mask = cv2.resize(mask_np, (config.IMG_SIZE[1], config.IMG_SIZE[0]), interpolation=cv2.INTER_LINEAR)
                        binary_mask = (resized_mask > 0.5).astype(np.uint8) * 255
                        combined_mask = cv2.bitwise_or(combined_mask, binary_mask)

                    people_mask = combined_mask
                else:
                    logger.debug("No persons detected",
                               image_path=image_path)

            # If no people mask was generated, return None
            if people_mask is None:
                return None
                
            return people_mask.reshape(people_mask.shape[0], people_mask.shape[1], 1)

        except Exception as e:
            logger.error("Item processing failed",
                        image_path=image_path,
                        error=str(e),
                        error_type=type(e).__name__)
            return None

    def cleanup(self) -> None:
        """Cleanup model resources."""
        logger.info("Cleaning up model resources",
                   model_name=self.model_name)
        self._model = None
        self._initialized = False

    @property
    def model_name(self) -> str:
        """Return the name of the segmentation model."""
        return "yolo11l-seg"

    @property
    def is_initialized(self) -> bool:
        """Return whether the model is initialized and ready for inference."""
        return self._initialized
