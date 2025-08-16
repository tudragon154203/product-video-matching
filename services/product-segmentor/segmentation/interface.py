"""Abstract segmentation interface for pluggable segmentation models."""

from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class SegmentationInterface(ABC):
    """Abstract interface for segmentation models."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the segmentation model.
        
        This method should load the model, download weights if needed,
        and prepare the model for inference.
        
        Raises:
            Exception: If model initialization fails
        """
        pass
    
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
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup model resources.
        
        This method should release any GPU memory, close model handles,
        and clean up temporary resources.
        """
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the name of the segmentation model."""
        pass
    
    @property
    @abstractmethod
    def is_initialized(self) -> bool:
        """Return whether the model is initialized and ready for inference."""
        pass