"""RMBG (Remove Background) segmentation implementation using Hugging Face transformers."""

import os
import asyncio
from typing import Optional
import numpy as np
from PIL import Image
import torch
from transformers import AutoModelForImageSegmentation, AutoProcessor
from common_py.logging_config import configure_logging

from .interface import SegmentationInterface

logger = configure_logging("rmbg-segmentor")


class RMBGSegmentor(SegmentationInterface):
    """RMBG segmentation model implementation."""
    
    def __init__(self, model_name: str = "briaai/RMBG-1.4", cache_dir: Optional[str] = None):
        """Initialize RMBG segmentor.
        
        Args:
            model_name: Hugging Face model name
            cache_dir: Directory to cache model files
        """
        self._model_name = model_name
        self._cache_dir = cache_dir
        self._model = None
        self._processor = None
        self._device = None
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the RMBG model."""
        try:
            logger.info("Initializing RMBG segmentation model", model_name=self._model_name)
            
            # Determine device (GPU if available, otherwise CPU)
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("Using device for segmentation", device=self._device)
            
            # Load model and processor in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Load processor
            self._processor = await loop.run_in_executor(
                None, 
                lambda: AutoProcessor.from_pretrained(
                    self._model_name,
                    cache_dir=self._cache_dir
                )
            )
            
            # Load model
            self._model = await loop.run_in_executor(
                None,
                lambda: AutoModelForImageSegmentation.from_pretrained(
                    self._model_name,
                    cache_dir=self._cache_dir,
                    torch_dtype=torch.float32
                )
            )
            
            # Move model to device
            self._model = self._model.to(self._device)
            self._model.eval()
            
            self._initialized = True
            logger.info("RMBG model initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize RMBG model", error=str(e))
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
            
            # Load image
            image = await loop.run_in_executor(
                None,
                lambda: Image.open(image_path).convert("RGB")
            )
            
            # Process image
            inputs = await loop.run_in_executor(
                None,
                lambda: self._processor(image, return_tensors="pt")
            )
            
            # Move inputs to device
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            
            # Run inference
            with torch.no_grad():
                outputs = await loop.run_in_executor(
                    None,
                    lambda: self._model(**inputs)
                )
            
            # Process output to binary mask
            mask = await loop.run_in_executor(
                None,
                self._process_output,
                outputs,
                image.size
            )
            
            logger.debug("Image segmentation completed", path=image_path)
            return mask
            
        except Exception as e:
            logger.error("Segmentation failed", path=image_path, error=str(e))
            return None
    
    def _process_output(self, outputs, original_size):
        """Process model output to binary mask."""
        # Get the segmentation logits
        logits = outputs.logits
        
        # Apply sigmoid and threshold
        probs = torch.sigmoid(logits)
        mask = (probs > 0.5).float()
        
        # Convert to numpy and resize to original image size
        mask_np = mask.squeeze().cpu().numpy()
        
        # Resize mask to original image size
        mask_pil = Image.fromarray((mask_np * 255).astype(np.uint8))
        mask_resized = mask_pil.resize(original_size, Image.NEAREST)
        
        # Convert back to numpy array
        return np.array(mask_resized)
    
    def cleanup(self) -> None:
        """Cleanup RMBG model resources."""
        try:
            if self._model is not None:
                del self._model
                self._model = None
                
            if self._processor is not None:
                del self._processor
                self._processor = None
                
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