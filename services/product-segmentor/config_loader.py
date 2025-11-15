"""
Configuration loader for Product Segmentor Service.
Uses environment variables directly since Docker Compose loads both shared and service-specific .env files.
"""
import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

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
    FOREGROUND_SEG_MODEL_NAME: str = os.getenv("FOREGROUND_SEG_MODEL_NAME", "briaai/RMBG-1.4")
    PEOPLE_SEG_MODEL_NAME: str = os.getenv("PEOPLE_SEG_MODEL_NAME", "yolo11l-seg")
    HF_TOKEN = os.getenv("HF_TOKEN")

    # Processing configuration
    MAX_CONCURRENT_IMAGES: int = int(os.getenv("MAX_CONCURRENT_IMAGES", "4"))
    BATCH_TIMEOUT_SECONDS: int = int(os.getenv("BATCH_TIMEOUT_SECONDS", "900"))
    MASK_QUALITY: float = float(os.getenv("MASK_QUALITY", "0.8"))
    IMG_SIZE: tuple[int, int] = global_config.IMG_SIZE

    # File paths
    FOREGROUND_MASK_DIR_PATH: str = os.path.join(global_config.DATA_ROOT_CONTAINER,
                                                 os.getenv("FOREGROUND_MASK_REL_PATH", "./masks_foreground"))
    PEOPLE_MASK_DIR_PATH: str = os.path.join(global_config.DATA_ROOT_CONTAINER, os.getenv("PEOPLE_MASK_REL_PATH", "./masks_people"))
    PRODUCT_MASK_DIR_PATH: str = os.path.join(global_config.DATA_ROOT_CONTAINER, os.getenv("PRODUCT_MASK_REL_PATH", "./masks_product"))

    # Database configuration (from global config)
    POSTGRES_DSN: str = global_config.POSTGRES_DSN

    # Message broker configuration (from global config)
    BUS_BROKER: str = global_config.BUS_BROKER

    # Data root (from global config)
    MODEL_CACHE: str = global_config.MODEL_CACHE

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", global_config.LOG_LEVEL)


# Create config instance
config = ProductSegmentorConfig()
