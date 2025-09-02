"""RMBG (Remove Background) segmentation implementation using Hugging Face transformers for version 1.4."""

import os
import asyncio
from typing import Optional
import numpy as np
from PIL import Image
import torch
from torchvision import transforms
from transformers import AutoModelForImageSegmentation
from common_py.logging_config import configure_logging

from segmentation.base_segmentation import BaseSegmentation
from segmentation.segmentation_utils import prepare_image, normalize_and_resize_mask # New import

logger = configure_logging("product-segmentor:rmbg14_segmentor")

from config_loader import config


class RMBG14Segmentor(BaseSegmentation):
    """RMBG-1.4 segmentation model implementation."""
    
    def __init__(self):
        """Initialize RMBG-1.4 segmentor."""
        super().__init__()
        self._model_name = "briaai/RMBG-1.4"
        self._model = None
        self._transform = None
        self._device = None
        self._image_size = (512, 512)
        
    async def initialize(self) -> None:
        """Initialize the RMBG-1.4 model."""
        try:
            logger.info("Initializing RMBG-1.4 segmentation model", model_name=self._model_name)
            
            # Determine device (GPU if available, otherwise CPU)
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("Using device for segmentation", device=self._device)
            
            # Set matmul precision for better performance
            if self._device == "cuda":
                torch.set_float32_matmul_precision('high')
            
            # Load model in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            logger.info("Loading RMBG-1.4 model", model_name=self._model_name)
            # Load model 
            self._model = await loop.run_in_executor(
                None,
                lambda: AutoModelForImageSegmentation.from_pretrained(
                    self._model_name,
                    trust_remote_code=True,  # Allow custom code execution
                    token=config.HF_TOKEN
                )
            )
            
            # Move model to device and set to eval mode
            self._model = self._model.to(self._device)
            self._model.eval()
            
            # Setup image transforms with RMBG-1.4 specific normalization
            self._transform = transforms.Compose([
                transforms.Resize(self._image_size),
                transforms.ToTensor(),
                transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])  # RMBG-1.4 specific normalization
            ])
            
            logger.info("RMBG-1.4 model initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize RMBG-1.4 model", error=str(e))
            logger.error("Make sure you have the latest transformers and torchvision installed")
            self._initialized = False
            raise
    
    async def segment_image(self, image_path: str) -> Optional[np.ndarray]:
        """Generate product mask using RMBG-1.4 model.
        
        Args:
            image_path: Path to input image
            
        Returns:
            Binary mask as numpy array or None if segmentation fails
        """
        if not self._initialized:
            logger.error("Model not initialized")
            return None
            
        if not os.path.exists(image_path):
            logger.error("Image file not found", path=image_path)
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        try:
            loop = asyncio.get_event_loop()
            image, input_tensor = await loop.run_in_executor(
                None,
                prepare_image,
                image_path, self._transform, self._device
            )
            
            preds = await self._run_inference(input_tensor, loop)
            
            mask = await loop.run_in_executor(
                None,
                normalize_and_resize_mask,
                preds,
                image.size
            )
            return mask
            
        except Exception as e:
            logger.error("Segmentation failed", path=image_path, error=str(e))
            return None
    
    async def _run_inference(self, input_tensor: torch.Tensor, loop: asyncio.BaseEventLoop) -> torch.Tensor:
        with torch.no_grad():
            logits = await loop.run_in_executor(
                None,
                lambda: self._model(input_tensor)
            )
            
            if isinstance(logits, (list, tuple)):
                last_output = logits[-1]
                if isinstance(last_output, torch.Tensor):
                    preds = torch.sigmoid(last_output).cpu()
                else:
                    if isinstance(last_output, (list, tuple)) and len(last_output) > 0:
                        inner_item = last_output[0]
                        if isinstance(inner_item, torch.Tensor):
                            preds = torch.sigmoid(inner_item).cpu()
                        else:
                            logger.error(f"Unexpected type in logits[-1][0]: {type(inner_item)}")
                            raise TypeError(f"Expected Tensor, got {type(inner_item)}")
                    else:
                        logger.error(f"Unexpected type in logits[-1]: {type(last_output)}")
                        raise TypeError(f"Expected Tensor, got {type(last_output)}")
            elif isinstance(logits, torch.Tensor):
                preds = torch.sigmoid(logits).cpu()
            else:
                logger.error(f"Unexpected model output type: {type(logits)}")
                raise TypeError(f"Expected Tensor or list/tuple, got {type(logits)}")
        return preds
    
    def cleanup(self) -> None:
        """Cleanup RMBG-1.4 model resources."""
        try:
            if self._model is not None:
                del self._model
                self._model = None
                
            if self._transform is not None:
                self._transform = None
                
            # Clear GPU cache if using CUDA
            if self._device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("RMBG-1.4 model resources cleaned up")
            
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))
    
    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self._model_name
    
    
