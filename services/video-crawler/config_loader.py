"""
Configuration loader for the video crawler service.
Uses environment variables directly since Docker Compose loads both shared and service-specific .env files.
"""
import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

# Add libs directory to PYTHONPATH for imports
sys.path.insert(0, '/app/libs')

try:
    from config import config as global_config
except ImportError:
    # Fallback for local development
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from libs.config import config as global_config

@dataclass
class VideoCrawlerConfig:
    """Configuration for the video crawler service"""
    
    # Database configuration (from global config)
    POSTGRES_DSN: str = global_config.POSTGRES_DSN
    POSTGRES_USER: str = global_config.POSTGRES_USER
    POSTGRES_PASSWORD: str = global_config.POSTGRES_PASSWORD
    POSTGRES_HOST: str = global_config.POSTGRES_HOST
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = global_config.POSTGRES_DB
    
    # Message broker configuration (from global config)
    BUS_BROKER: str = global_config.BUS_BROKER
    
    # Data storage (from global config)
    DATA_ROOT: str = global_config.DATA_ROOT_CONTAINER
    
    # Video storage directory
    VIDEO_DIR: str = os.getenv("VIDEO_DIR", os.path.join(global_config.DATA_ROOT_CONTAINER, "videos"))
    
    # Number of videos to search for per query
    NUM_VIDEOS: int = int(os.getenv("NUM_VIDEOS", "5"))
    
    # Number of concurrent video downloads
    NUM_PARALLEL_DOWNLOADS: int = int(os.getenv("NUM_PARALLEL_DOWNLOADS", "5"))
    
    # Logging (from .env first, then global config)
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", global_config.LOG_LEVEL)
    
    # TikTok API Configuration
    TIKTOK_MS_TOKEN: str = os.getenv("TIKTOK_MS_TOKEN", "")
    TIKTOK_BROWSER: str = os.getenv("TIKTOK_BROWSER", "chromium")
    TIKTOK_HEADLESS: bool = os.getenv("TIKTOK_HEADLESS", "true").lower() == "true"
    TIKTOK_PROXY_URL: str = os.getenv("TIKTOK_PROXY_URL", "")  # Not needed for Vietnam IP
    TIKTOK_MAX_RETRIES: int = int(os.getenv("TIKTOK_MAX_RETRIES", "3"))
    TIKTOK_SLEEP_AFTER: int = int(os.getenv("TIKTOK_SLEEP_AFTER", "2"))  # Reduced for Vietnam IP
    TIKTOK_SESSION_COUNT: int = int(os.getenv("TIKTOK_SESSION_COUNT", "1"))
    TIKTOK_VIETNAM_REGION: bool = os.getenv("TIKTOK_VIETNAM_REGION", "true").lower() == "true"

# Create config instance
config = VideoCrawlerConfig()