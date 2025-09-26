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
    
    # Video storage directory
    VIDEO_DIR: str = os.path.join(global_config.DATA_ROOT_CONTAINER, os.getenv("VIDEO_REL_PATH", "videos"))
    KEYFRAME_DIR: str = os.path.join(global_config.DATA_ROOT_CONTAINER, os.getenv("KEYFRAME_REL_PATH", "keyframes"))

    # Number of videos to search for per query
    NUM_VIDEOS: int = int(os.getenv("NUM_VIDEOS", "5"))
    
    # Number of concurrent video downloads (reduced to avoid 403 errors)
    NUM_PARALLEL_DOWNLOADS: int = int(os.getenv("NUM_PARALLEL_DOWNLOADS", "3"))  # Reduced from 5 to 3
    
    # Maximum number of concurrent platforms (-1 means no limit, default to len(platforms))
    MAX_CONCURRENT_PLATFORMS: int = int(os.getenv("MAX_CONCURRENT_PLATFORMS", "-1"))
    
    # Logging (from .env first, then global config)
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", global_config.LOG_LEVEL)
    
    # Proxy configuration
    USE_PRIVATE_PROXY: bool = os.getenv("USE_PRIVATE_PROXY", "false").lower() == "true"
    PRIVATE_SOCKS5_PROXY: str = os.getenv("PRIVATE_SOCKS5_PROXY", "socks5://localhost:1080")
    
    # Video cleanup configuration
    CLEANUP_OLD_VIDEOS: bool = os.getenv("CLEANUP_OLD_VIDEOS", "false").lower() == "true"
    VIDEO_RETENTION_DAYS: int = int(os.getenv("VIDEO_RETENTION_DAYS", "7"))

    # TikTok API configuration
    TIKTOK_CRAWL_HOST_PORT: str = os.getenv("TIKTOK_CRAWL_HOST_PORT", "5680")
    

# Create config instance
config = VideoCrawlerConfig()
