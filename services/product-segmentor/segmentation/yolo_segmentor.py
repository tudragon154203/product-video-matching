from ultralytics import YOLO
import numpy as np
import cv2
import os
from typing import Optional

from segmentation.interface import SegmentationInterface
from config_loader import config

class YOLOSegmentor(SegmentationInterface):
    """YOLOv8 segmentation model for people segmentation."""

    def __init__(self, model_name: str = 'yolo11l-seg.pt'):
        self._model_path = os.path.join(config.PEOPLE_SEG_MODEL_CACHE, model_name)
        self._model: Optional[YOLO] = None
        self._initialized = False
        # Set the YOLO_MODEL_DIR environment variable for ultralytics library
        os.environ['YOLO_MODEL_DIR'] = config.PEOPLE_SEG_MODEL_CACHE

    async def initialize(self) -> None:
        """Initialize the YOLO segmentation model."""
        try:
            print(f"Initializing YOLO segmentor with model: {self._model_path}")
            self._model = YOLO(self._model_path)
            self._initialized = True
            print("YOLO segmentor initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize YOLO segmentor: {e}")
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
                    print(f"No persons detected or no masks generated for {image_path}.")

            return people_mask.reshape(people_mask.shape[0], people_mask.shape[1], 1)

        except Exception as e:
            print(f"Error during YOLO segmentation for {image_path}: {e}")
            return None

    def cleanup(self) -> None:
        """Cleanup model resources."""
        print("Cleaning up YOLO segmentor resources.")
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
