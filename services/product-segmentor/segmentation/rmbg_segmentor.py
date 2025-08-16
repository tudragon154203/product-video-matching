"""RMBG (Remove Background) segmentation implementation using Hugging Face transformers."""

import os
import asyncio
from typing import Optional
import numpy as np
from PIL import Image
import torch
from torchvision import transforms
from transformers import AutoModelForImageSegmentation
from common_py.logging_config import configure_logging

from .interface import SegmentationInterface

logger = configure_logging("rmbg-segmentor")


class RMBGSegmentor(SegmentationInterface):
    """RMBG segmentation model implementation."""
    
    def __init__(self, model_name: str = "briaai/RMBG-2.0"):
        """Initialize RMBG segmentor.
        
        Args:
            model_name: Hugging Face model name
        """
        self._model_name = model_name
        self._model = None
        self._transform = None
        self._device = None
        self._initialized = False
        self._image_size = (512, 512)
        
    async def initialize(self) -> None:
        """Initialize the RMBG model."""
        try:
            logger.info("Initializing RMBG segmentation model", model_name=self._model_name)
            
            # Determine device (GPU if available, otherwise CPU)
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("Using device for segmentation", device=self._device)
            
            # Set matmul precision for better performance
            if self._device == "cuda":
                torch.set_float32_matmul_precision('high')
            
            # Load model in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            logger.info("Loading RMBG-2.0 model with trust_remote_code=True", model_name=self._model_name)
            # Load model
            self._model = await loop.run_in_executor(
                None,
                lambda: AutoModelForImageSegmentation.from_pretrained(
                    self._model_name,
                    trust_remote_code=True  # Allow custom code execution
                )
            )
            
            # Move model to device and set to eval mode
            self._model = self._model.to(self._device)
            self._model.eval()
            
            # Setup image transforms
            self._transform = transforms.Compose([
                transforms.Resize(self._image_size),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
            ])
            
            self._initialized = True
            logger.info("RMBG-2.0 model initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize RMBG model", error=str(e))
            logger.error("Make sure you have the latest transformers and torchvision installed")
            self._initialized = False
            raise
    
    async def segment_image(self, image_path: str) -> Optional[np.ndarray]:
        """Generate product mask using RMBG model.
        
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
            logger.debug("Processing image for segmentation", path=image_path)
            
            # Load and process image in executor
            loop = asyncio.get_event_loop()
            
            # Load and transform image
            image, input_tensor = await loop.run_in_executor(
                None,
                self._prepare_image,
                image_path
            )
            
            # Run inference
            with torch.no_grad():
                preds = await loop.run_in_executor(
                    None,
                    lambda: self._model(input_tensor)[-1].sigmoid().cpu()
                )
            
            # Process output to binary mask
            mask = await loop.run_in_executor(
                None,
                self._process_output,
                preds,
                image.size
            )
            
            logger.debug("Image segmentation completed", path=image_path)
            return mask
            
        except Exception as e:
            logger.error("Segmentation failed", path=image_path, error=str(e))
            return None
    
    def _prepare_image(self, image_path: str):
        """Prepare image for inference."""
        # Load image
        image = Image.open(image_path).convert("RGB")
        
        # Transform image
        input_tensor = self._transform(image).unsqueeze(0).to(self._device)
        
        return image, input_tensor
    
    def _process_output(self, preds, original_size):
        """Process model output to binary mask."""
        # Get the prediction
        pred = preds[0].squeeze()
        
        # Convert to PIL image
        pred_pil = transforms.ToPILImage()(pred)
        
        # Resize mask to original image size
        mask_resized = pred_pil.resize(original_size, Image.NEAREST)
        
        # Convert to numpy array (0-255 range)
        mask_np = np.array(mask_resized)
        
        # Ensure it's in the right format (0-255 uint8)
        if mask_np.dtype != np.uint8:
            mask_np = (mask_np * 255).astype(np.uint8)
        
        return mask_np
    
    def cleanup(self) -> None:
        """Cleanup RMBG model resources."""
        try:
            if self._model is not None:
                del self._model
                self._model = None
                
            if self._transform is not None:
                self._transform = None
                
            # Clear GPU cache if using CUDA
            if self._device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            self._initialized = False
            logger.info("RMBG model resources cleaned up")
            
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))
    
    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self._model_name
    
    @property
    def is_initialized(self) -> bool:
        """Return whether the model is initialized."""
        return self._initialized