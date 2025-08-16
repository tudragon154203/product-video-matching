"""Factory for creating segmentation engines."""

from typing import Optional
from segmentation.interface import SegmentationInterface
from segmentation.rmbg_segmentor import RMBGSegmentor


def create_segmentor(model_name: str, hf_token: Optional[str] = None) -> SegmentationInterface:
    """Create segmentation engine based on model name.
    
    Args:
        model_name: Hugging Face model name
        hf_token: Optional Hugging Face token for private models
        
    Returns:
        SegmentationInterface instance
        
    Raises:
        ValueError: If model type is not supported
    """
    # For now, we only support RMBG models
    # In the future, we can detect model type from model_name or add a separate parameter
    return RMBGSegmentor(model_name=model_name)