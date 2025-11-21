"""
Configuration loader for the video crawler service.
Uses environment variables directly since Docker Compose loads both shared and service-specific .env files.
"""
import os
import sys
import logging
from dataclasses import dataclass, field
from urllib.parse import urlparse

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

# Configure a lightweight logger for startup diagnostics
try:
    from common_py.logging_config import configure_logging
    logger = configure_logging("video-crawler:config")
except Exception:
    logger = logging.getLogger("video-crawler:config")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)


def _get_effective_dsn() -> str:
    """
    Resolve Postgres DSN with explicit precedence:
    1) POSTGRES_DSN
    2) DATABASE_URL
    3) POSTGRES_URI
    Fallback to global_config.POSTGRES_DSN if none are set.
    """
    for key in ("POSTGRES_DSN", "DATABASE_URL", "POSTGRES_URI"):
        val = os.getenv(key, "").strip()
        if val:
            return val
    return global_config.POSTGRES_DSN

@dataclass
class PySceneDetectSettings:
    """Internal configuration for the PySceneDetect strategy."""

    adaptive_threshold: float = 3.0
    min_scene_len: int = 15
    window_width: int = 2
    min_content_val: float = 15.0
    weights_luma_only: bool = False
    min_scene_duration_seconds: float = 0.5
    boundary_guard_seconds: float = 0.15
    fallback_offset_seconds: float = 0.25
    min_blur_threshold: float = 100.0
    frame_quality: int = 90
    frame_format: str = "jpg"
    max_scenes: int = 0  # 0 => unlimited timestamps


@dataclass
class PyAVSettings:
    """Internal configuration for the PyAV strategy."""

    enable_pyav_routing: bool = True
    fallback_to_pyscene: bool = os.getenv("PYAV_FALLBACK_TO_PYSCENE", "true").lower() == "true"
    frame_quality: int = int(os.getenv("PYAV_QUALITY", os.getenv("PYAV_FRAME_QUALITY", "90")))
    frame_format: str = os.getenv("PYAV_FORMAT", os.getenv("PYAV_FRAME_FORMAT", "jpg"))
    max_frames: int = int(os.getenv("PYAV_MAX_FRAMES", "5"))
    min_blur_threshold: float = float(os.getenv("PYAV_MIN_BLUR_THRESHOLD", "100.0"))
    boundary_guard_seconds: float = float(os.getenv("PYAV_BOUNDARY_GUARD_SECONDS", "0.25"))
    seek_tolerance_seconds: float = float(os.getenv("PYAV_SEEK_TOLERANCE_SECONDS", "1.0"))


@dataclass
class VideoCrawlerConfig:
    """Configuration for the video crawler service"""

    # Database configuration with robust env precedence (no localhost defaults here)
    POSTGRES_DSN: str = _get_effective_dsn()
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
    TIKTOK_CRAWL_HOST: str = os.getenv("TIKTOK_CRAWL_HOST", "host.docker.internal")
    TIKTOK_CRAWL_HOST_PORT: str = os.getenv("TIKTOK_CRAWL_HOST_PORT", "5680")

    # TikTok download strategy configuration
    TIKTOK_DOWNLOAD_STRATEGY: str = os.getenv("TIKTOK_DOWNLOAD_STRATEGY", "scrapling-api")
    TIKTOK_DOWNLOAD_TIMEOUT: int = int(os.getenv("TIKTOK_DOWNLOAD_TIMEOUT", "180"))

    # TikTok storage paths
    TIKTOK_VIDEO_STORAGE_PATH: str = os.path.join(global_config.DATA_ROOT_CONTAINER, 'videos', 'tiktok')
    TIKTOK_KEYFRAME_STORAGE_PATH: str = os.path.join(global_config.DATA_ROOT_CONTAINER, 'keyframes', 'tiktok')

    # Scene detection tuning
    PYSCENEDETECT_SETTINGS: PySceneDetectSettings = field(default_factory=PySceneDetectSettings)
    PYAV_SETTINGS: PyAVSettings = field(default_factory=PyAVSettings)


# Create config instance
config = VideoCrawlerConfig()

# Safe one-line startup log with DB host and database name (mask credentials)
try:
    parsed = urlparse(config.POSTGRES_DSN)
    db_host = parsed.hostname or "unknown-host"
    db_name = (parsed.path or "").lstrip("/") or "unknown-db"
    logger.info(f"Database target resolved: host={db_host}, db={db_name}")
except Exception:
    logger.info("Database target resolved: host=?, db=?")
