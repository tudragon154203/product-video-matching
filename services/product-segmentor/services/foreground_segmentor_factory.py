"""Factory for creating segmentation engines."""

from typing import Optional
from segmentation.interface import SegmentationInterface
from segmentation.models.rmbg20_segmentor import RMBG20Segmentor
from segmentation.models.rmbg14_segmentor import RMBG14Segmentor
from common_py.logging_config import configure_logging

logger = configure_logging("product-segmentor:foreground_segmentor_factory")


def create_segmentor(model_name: Optional[str] = None, hf_token: Optional[str] = None) -> SegmentationInterface:
    """Create segmentation engine based on model name or configuration.

    Args:
        model_name: Optional Hugging Face model name. If None, uses config default.
        hf_token: Optional Hugging Face token for private models

    Returns:
        SegmentationInterface instance

    Raises:
        ValueError: If model type is not supported
    """
    # Import config here to avoid circular imports
    from config_loader import config

    # Use provided model_name or fall back to config
    if model_name is None:
        model_name = config.FOREGROUND_SEG_MODEL_NAME

    # Detect RMBG version and create appropriate segmentor
    if "RMBG-1.4" in model_name or "rmbg-1.4" in model_name:
        return RMBG14Segmentor()
    elif "RMBG-2.0" in model_name or "rmbg-2.0" in model_name:
        return RMBG20Segmentor()
    else:
        # Default to RMBG-2.0 for backward compatibility
        logger.warning(f"Unknown RMBG model version, defaulting to RMBG-2.0: {model_name}")
        return RMBG20Segmentor()
