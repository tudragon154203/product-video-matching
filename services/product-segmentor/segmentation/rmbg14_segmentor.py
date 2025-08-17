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

from .interface import SegmentationInterface

logger = configure_logging("rmbg14-segmentor")

from config_loader import config


class RMBG14Segmentor(SegmentationInterface):
    """RMBG-1.4 segmentation model implementation."""
    
    def __init__(self):
        """Initialize RMBG-1.4 segmentor."""
        self._model_name = "briaai/RMBG-1.4"
        self._model = None
        self._transform = None
        self._device = None
        self._initialized = False
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
            
            self._initialized = True
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
                # RMBG-1.4 outputs raw logits, need to apply sigmoid
                logits = await loop.run_in_executor(
                    None,
                    lambda: self._model(input_tensor)
                )
                
                if isinstance(logits, (list, tuple)):
                    # If logits is a list/tuple, get the last element
                    last_output = logits[-1]
                    if isinstance(last_output, torch.Tensor):
                        preds = torch.sigmoid(last_output).cpu()
                    else:
                        # Handle case where last_output is still a list/tuple
                        if isinstance(last_output, (list, tuple)) and len(last_output) > 0:
                            # Try to get the first tensor from the nested structure
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
                    # If logits is a single tensor
                    preds = torch.sigmoid(logits).cpu()
                else:
                    logger.error(f"Unexpected model output type: {type(logits)}")
                    raise TypeError(f"Expected Tensor or list/tuple, got {type(logits)}")
            
            # Process output to binary mask
            mask = await loop.run_in_executor(
                None,
                self._process_output,
                preds,
                image.size
            )
            return mask
            
        except Exception as e:
            logger.error("Segmentation failed", path=image_path, error=str(e))
            return None
    
    def _prepare_image(self, image_path: str):
        """Prepare image for inference."""
        # Load image
        image = Image.open(image_path)

        # Convert to RGBA first to handle potential alpha channels, then to RGB
        # This can sometimes resolve issues with images having unusual modes
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        image = image.convert('RGB')

        # Transform image
        input_tensor = self._transform(image).unsqueeze(0).to(self._device)

        return image, input_tensor
    
    def _process_output(self, preds, original_size):
        """Process model output to binary mask."""
        try:
            # Get the prediction
            # Handle different possible structures of preds
            if isinstance(preds, (list, tuple)):
                # If preds is a list/tuple, get the first element
                pred = preds[0]
            else:
                # If preds is already a tensor, use it directly
                pred = preds
            
            # Squeeze to remove unnecessary dimensions
            pred = pred.squeeze()
            
            # Ensure we have the right number of channels for ToPILImage
            # If we still have multiple channels, take the first one (mask channel)
            if isinstance(pred, torch.Tensor) and pred.dim() > 2:
                # For segmentation masks, we typically want the first channel
                pred = pred[0] if pred.shape[0] <= pred.shape[1] and pred.shape[0] <= pred.shape[2] else pred[:, :, 0]
            
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
        except Exception as e:
            logger.error(f"Error processing model output: {e}")
            raise
    
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
                
            self._initialized = False
            logger.info("RMBG-1.4 model resources cleaned up")
            
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