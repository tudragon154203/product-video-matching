"""Abstract segmentation interface for pluggable segmentation models."""

from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class SegmentationInterface(ABC):
    """Abstract interface for segmentation models."""

    @abstractmethod
    async def segment_image(self, image_path: str) -> Optional[np.ndarray]:
        """Generate product mask for image.

        Args:
            image_path: Path to input image file

        Returns:
            Binary mask as numpy array (0=background, 255=foreground)
            or None if segmentation fails

        Raises:
            FileNotFoundError: If image file doesn't exist
            Exception: If segmentation processing fails
        """
        raise NotImplementedError
