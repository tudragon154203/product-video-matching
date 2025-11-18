from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from transformers import CLIPModel, CLIPProcessor as CLIPProcessorTransformers

from common_py.logging_config import configure_logging

logger = configure_logging("vision-embedding:clip_processor")


class CLIPProcessor:
    def __init__(
        self,
        model: CLIPModel,
        processor: CLIPProcessorTransformers,
        device: torch.device,
    ) -> None:
        self.model = model
        self.processor = processor
        self.device = device

    async def extract_clip_embeddings(
        self, image: Image.Image
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Extract real CLIP embeddings."""
        import time
        start_time = time.time()
        
        with torch.no_grad():
            # RGB embedding
            rgb_inputs = self.processor(images=image, return_tensors="pt")
            rgb_inputs = {
                key: value.to(self.device)
                for key, value in rgb_inputs.items()
            }
            rgb_features = self.model.get_image_features(**rgb_inputs)
            rgb_embedding = F.normalize(
                rgb_features,
                p=2,
                dim=1,
            ).cpu().numpy()[0]

            # Grayscale embedding
            gray_image = image.convert("L").convert(
                "RGB"
            )  # Convert to grayscale then back to RGB
            gray_inputs = self.processor(
                images=gray_image,
                return_tensors="pt",
            )
            gray_inputs = {
                key: value.to(self.device)
                for key, value in gray_inputs.items()
            }
            gray_features = self.model.get_image_features(**gray_inputs)
            gray_embedding = F.normalize(
                gray_features,
                p=2,
                dim=1,
            ).cpu().numpy()[0]
            
            total_time = time.time() - start_time
            
            logger.info(
                "CLIP embedding extraction",
                time_ms=round(total_time * 1000, 2),
                device=str(self.device),
            )

            return rgb_embedding, gray_embedding

    async def extract_embeddings_with_mask(
        self,
        image_path: str,
        mask_path: str,
        img_size: Tuple[int, int],
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Extract RGB and grayscale embeddings from an image with a mask."""
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert("RGB")

            # Resize image to img_size
            if image.size != img_size:
                image = image.resize(
                    img_size,
                    Image.LANCZOS,
                )  # Using LANCZOS for better quality resizing

            # Load mask
            mask = Image.open(mask_path).convert("L")

            # Resize mask to match image size if needed
            if mask.size != img_size:
                mask = mask.resize(img_size, Image.NEAREST)

            # Apply mask to image
            masked_image = self._apply_mask_to_image(image, mask)

            return await self.extract_clip_embeddings(masked_image)

        except Exception as e:
            logger.error(
                "Failed to extract embeddings with mask",
                image_path=image_path,
                mask_path=mask_path,
                error=str(e),
            )
            return None, None

    def _apply_mask_to_image(
        self, image: Image.Image, mask: Image.Image
    ) -> Image.Image:
        """Apply mask to image, setting background to black."""
        # Convert mask to numpy array
        mask_array = np.array(mask)

        # Normalize mask to 0-1 range
        mask_normalized = mask_array.astype(np.float32) / 255.0

        # Convert image to numpy array
        image_array = np.array(image)

        # Apply mask to each channel
        masked_array = image_array.copy()
        for channel in range(3):  # RGB channels
            masked_array[:, :, channel] = (
                masked_array[:, :, channel] * mask_normalized
            )

        # Convert back to PIL Image
        masked_image = Image.fromarray(masked_array.astype(np.uint8))

        return masked_image
