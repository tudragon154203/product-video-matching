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


def _parse_bool(value: str, default: str = "true") -> bool:
    """Parse boolean from environment variable.
    
    Accepts: 1, true, yes, enable (case-insensitive)
    Rejects: 0, false, no, disable (case-insensitive)
    """
    val = os.getenv(value, default).lower().strip()
    return val in ("1", "true", "yes", "enable")


@dataclass
class ProductSegmentorConfig:
    """Configuration for Product Segmentor Service."""

    # Segmentation model configuration
    FOREGROUND_SEG_MODEL_NAME: str = os.getenv("FOREGROUND_SEG_MODEL_NAME", "briaai/RMBG-1.4")
    PEOPLE_SEG_MODEL_NAME: str = os.getenv("PEOPLE_SEG_MODEL_NAME", "yolo11l-seg")
    HF_TOKEN = os.getenv("HF_TOKEN")

    # Processing configuration
    MAX_CONCURRENT_IMAGES_IN_BATCH: int = int(os.getenv("MAX_CONCURRENT_IMAGES_IN_BATCH", "3"))
    MAX_CONCURRENT_BATCHES: int = int(os.getenv("MAX_CONCURRENT_BATCHES", "2"))
    BATCH_TIMEOUT_SECONDS: int = int(os.getenv("BATCH_TIMEOUT_SECONDS", "1800"))
    MASK_QUALITY: float = float(os.getenv("MASK_QUALITY", "0.8"))
    IMG_SIZE: tuple[int, int] = global_config.IMG_SIZE

    # GPU Memory Management
    USE_FP16: bool = _parse_bool("USE_FP16", "true")
    RETRY_ON_OOM: bool = _parse_bool("RETRY_ON_OOM", "true")
    MAX_OOM_RETRIES: int = int(os.getenv("MAX_OOM_RETRIES", "3"))
    GPU_MEMORY_THRESHOLD: float = float(os.getenv("GPU_MEMORY_THRESHOLD", "0.85"))

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
