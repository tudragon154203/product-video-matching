from ultralytics import YOLO
import numpy as np
import cv2
import os
from typing import Optional

from segmentation.base_segmentation import BaseSegmentation
from config_loader import config
from common_py.logging_config import configure_logging

logger = configure_logging("product-segmentor:yolo_segmentor")


class YOLOSegmentor(BaseSegmentation):
    """YOLOv8 segmentation model for people segmentation."""

    def __init__(self, model_name: str = 'yolo11l-seg'):
        super().__init__()
        # Store the base model name without extension
        self._model_name = model_name
        # Ensure model name has .pt extension for file path
        model_filename = model_name if model_name.endswith('.pt') else f"{model_name}.pt"

        # Determine the correct model cache path
        # Always use configured MODEL_CACHE for consistency in tests and local dev
        model_cache_dir = config.MODEL_CACHE

        self._model_path = os.path.join(model_cache_dir, model_filename)
        self._model_cache_dir = model_cache_dir
        self._model: Optional[YOLO] = None

    async def initialize(self) -> None:
        """Initialize the YOLO segmentation model."""
        try:
            logger.info("Initializing model",
                        model_name=self.model_name,
                        model_path=self._model_path,
                        cache_dir=self._model_cache_dir)

            # Ensure the model cache directory exists
            os.makedirs(self._model_cache_dir, exist_ok=True)

            # Check if model file already exists in our cache
            if os.path.exists(self._model_path):
                logger.info("Loading model from local cache",
                            model_path=self._model_path,
                            file_exists=os.path.exists(self._model_path))
                try:
                    self._model = YOLO(self._model_path)
                except Exception:
                    # Fallback: cached file might be corrupt, attempt clean download
                    logger.warning("Cached model corrupt, re-downloading",
                                   model_path=self._model_path)
                    os.remove(self._model_path)
                    # Proceed to download path below
            else:
                logger.info("Model not found in cache, downloading from Ultralytics hub",
                            model_name=self.model_name,
                            cache_dir=self._model_cache_dir,
                            expected_path=self._model_path,
                            cache_contents=os.listdir(self._model_cache_dir) if os.path.exists(self._model_cache_dir) else [])

                # Change to model cache directory temporarily to ensure model downloads there
                original_cwd = os.getcwd()
                try:
                    os.chdir(self._model_cache_dir)
                    # Download model from Ultralytics hub - will download to current directory
                    self._model = YOLO(self._model_name)

                    # Check if model file was created and move it to expected location if needed
                    downloaded_path = os.path.join(self._model_cache_dir, f"{self._model_name}.pt")
                    if os.path.exists(downloaded_path) and downloaded_path != self._model_path:
                        if os.path.exists(self._model_path):
                            os.remove(self._model_path)
                        os.rename(downloaded_path, self._model_path)

                finally:
                    # Restore original working directory
                    os.chdir(original_cwd)

            logger.info("Model initialized successfully",
                        model_name=self.model_name)
            # Mark as initialized using the base class method
            self._initialized = True
        except Exception as e:
            logger.error("Model initialization failed",
                         model_name=self.model_name,
                         model_path=self._model_path,
                         cache_dir=self._model_cache_dir,
                         working_dir=os.getcwd(),
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
                    # Get original image dimensions
                    orig_height, orig_width = r.masks.orig_shape[:2]

                    # Combine all person masks into a single mask with original dimensions
                    combined_mask = np.zeros((orig_height, orig_width), dtype=np.uint8)
                    for mask_tensor in r.masks.data:
                        mask_np = mask_tensor.cpu().numpy()
                        if mask_np.ndim == 3:
                            mask_np = mask_np.squeeze()

                        # Resize mask to original image dimensions (not config.IMG_SIZE)
                        resized_mask = cv2.resize(mask_np, (orig_width, orig_height), interpolation=cv2.INTER_LINEAR)
                        binary_mask = (resized_mask > 0.5).astype(np.uint8) * 255

                        # Ensure both masks have the same shape before bitwise operation
                        if combined_mask.shape == binary_mask.shape:
                            combined_mask = cv2.bitwise_or(combined_mask, binary_mask)
                        else:
                            logger.warning("Mask shape mismatch, skipping mask",
                                           combined_shape=combined_mask.shape,
                                           binary_shape=binary_mask.shape)

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
        return self._model_name

    @property
    def is_initialized(self) -> bool:
        """Return whether the model is initialized and ready for inference."""
        return self._initialized
