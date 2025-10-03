"""Configuration loader for the matcher service."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Add libs directory to PYTHONPATH for imports
sys.path.insert(0, "/app/libs")

try:
    from config import config as global_config
except ImportError:
    # Fallback for local development
    REPO_ROOT = Path(__file__).resolve().parents[2]
    sys.path.append(str(REPO_ROOT))
    from libs.config import config as global_config


@dataclass
class MatcherConfig:
    """Configuration for the matcher service."""

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

    # Matching parameters (from service environment)
    RETRIEVAL_TOPK: int = int(os.getenv("RETRIEVAL_TOPK", 20))
    SIM_DEEP_MIN: float = float(os.getenv("SIM_DEEP_MIN", 0.82))
    INLIERS_MIN: float = float(os.getenv("INLIERS_MIN", 0.35))
    MATCH_BEST_MIN: float = float(os.getenv("MATCH_BEST_MIN", 0.88))
    MATCH_CONS_MIN: int = int(os.getenv("MATCH_CONS_MIN", 2))
    MATCH_ACCEPT: float = float(os.getenv("MATCH_ACCEPT", 0.80))

    # Logging (from global config)
    LOG_LEVEL: str = global_config.LOG_LEVEL


config = MatcherConfig()
