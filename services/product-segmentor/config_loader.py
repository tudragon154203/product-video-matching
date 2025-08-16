"""
Configuration loader for Product Segmentor Service.
Uses environment variables directly since Docker Compose loads both shared and service-specific .env files.
"""
import os
import sys
from dataclasses import dataclass
from typing import Optional

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add libs directory to PYTHONPATH for imports
sys.path.insert(0, '/app/libs')

try:
    from config import config as global_config
except ImportError:
    # Fallback for local development
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from libs.config import config as global_config


@dataclass
class ProductSegmentorConfig:
    """Configuration for Product Segmentor Service."""
    
    # Segmentation model configuration
    SEGMENTATION_MODEL_NAME: str = os.getenv("SEGMENTATION_MODEL_NAME", "briaai/RMBG-1.4")
    HF_TOKEN = os.getenv("HF_TOKEN")

    # Processing configuration
    MAX_CONCURRENT_IMAGES: int = int(os.getenv("MAX_CONCURRENT_IMAGES", "4"))
    BATCH_TIMEOUT_SECONDS: int = int(os.getenv("BATCH_TIMEOUT_SECONDS", "300"))
    MASK_QUALITY: float = float(os.getenv("MASK_QUALITY", "0.8"))
    
    # File paths
    MASK_BASE_PATH: str = os.getenv("MASK_BASE_PATH", "data/masks")
    
    # Database configuration (from global config)
    POSTGRES_DSN: str = global_config.POSTGRES_DSN
    
    # Message broker configuration (from global config)
    BUS_BROKER: str = global_config.BUS_BROKER
    
    # Data root (from global config)
    DATA_ROOT: str = global_config.DATA_ROOT
    
    # Logging
    LOG_LEVEL: str = global_config.LOG_LEVEL


# Create config instance
config = ProductSegmentorConfig()