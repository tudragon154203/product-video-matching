"""Base abstract class for segmentation models with common functionality."""

from abc import ABC, abstractmethod
from typing import Optional
import numpy as np
from .interface import SegmentationInterface


class BaseSegmentation(SegmentationInterface):
    """Abstract base class for segmentation models with common infrastructure."""
    
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
    
    def __init__(self):
        """Initialize the base segmentation model."""
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the segmentation model.
        
        This method should load the model, download weights if needed,
        and prepare the model for inference.
        
        Raises:
            Exception: If model initialization fails
        """
        self._initialized = True
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup model resources.
        
        This method should release any GPU memory, close model handles,
        and clean up temporary resources.
        """
        self._initialized = False
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the name of the segmentation model."""
        pass
    
    @property
    def is_initialized(self) -> bool:
        """Return whether the model is initialized and ready for inference."""
        return self._initialized
    
    