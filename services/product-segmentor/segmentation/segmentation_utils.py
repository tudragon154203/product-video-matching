import os
import asyncio
from typing import Optional
import numpy as np
from PIL import Image
import torch
from torchvision import transforms
from common_py.logging_config import configure_logging

logger = configure_logging("product-segmentor:segmentation_utils")

def prepare_image(image_path: str, transform: transforms.Compose, device: torch.device):
    """Prepare image for inference."""
    # Load image
    image = Image.open(image_path)

    # Convert to RGBA first to handle potential alpha channels, then to RGB
    # This can sometimes resolve issues with images having unusual modes
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    image = image.convert('RGB')

    # Transform image
    input_tensor = transform(image).unsqueeze(0).to(device)

    return image, input_tensor

def normalize_and_resize_mask(preds: torch.Tensor, original_size: tuple) -> np.ndarray:
    """Process model output to binary mask."""
    try:
        if isinstance(preds, (list, tuple)):
            pred = preds[0]
        else:
            pred = preds
        
        pred = pred.squeeze()
        
        if isinstance(pred, torch.Tensor) and pred.dim() > 2:
            pred = pred[0] if pred.shape[0] <= pred.shape[1] and pred.shape[0] <= pred.shape[2] else pred[:, :, 0]
        
        pred_pil = transforms.ToPILImage()(pred)
        mask_resized = pred_pil.resize(original_size, Image.NEAREST)
        mask_np = np.array(mask_resized)
        
        if mask_np.dtype != np.uint8:
            mask_np = (mask_np * 255).astype(np.uint8)
        
        return mask_np
    except Exception as e:
        logger.error(f"Error processing model output: {e}")
        raise
