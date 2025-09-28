"""Configuration loader for the vision embedding service.

Environment variables are used directly because Docker Compose loads both the
shared and service-specific ``.env`` files.
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Add libs directory to PYTHONPATH for imports
sys.path.insert(0, "/app/libs")

try:
    from config import config as global_config
except ImportError:
    # Fallback for local development
    project_root = Path(__file__).resolve().parents[2]
    sys.path.append(str(project_root))
    from libs.config import config as global_config

@dataclass
class VisionEmbeddingConfig:
    """Configuration for the vision embedding service."""

    # Database configuration (from global config)
    POSTGRES_DSN: str = global_config.POSTGRES_DSN
    POSTGRES_USER: str = global_config.POSTGRES_USER
    POSTGRES_PASSWORD: str = global_config.POSTGRES_PASSWORD
    POSTGRES_HOST: str = global_config.POSTGRES_HOST
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = global_config.POSTGRES_DB

    # Message broker configuration (from global config)
    BUS_BROKER: str = global_config.BUS_BROKER

    # Vision model (from global config)
    EMBED_MODEL: str = global_config.EMBED_MODEL
    IMG_SIZE: tuple[int, int] = global_config.IMG_SIZE

    # Logging (from global config)
    LOG_LEVEL: str = global_config.LOG_LEVEL

config = VisionEmbeddingConfig()
