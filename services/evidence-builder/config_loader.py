"""Configuration loader for the evidence builder service."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

SERVICE_DIR = Path(__file__).resolve().parent
load_dotenv(SERVICE_DIR / ".env")

LIBS_PATH = Path("/app/libs")
if str(LIBS_PATH) not in sys.path:
    sys.path.insert(0, str(LIBS_PATH))

try:
    from config import config as global_config
except ImportError:  # pragma: no cover - dev fallback
    project_root = SERVICE_DIR.parents[2]
    sys.path.append(str(project_root))
    from libs.config import config as global_config


@dataclass
class EvidenceBuilderConfig:
    """Configuration for the evidence builder service."""

    POSTGRES_DSN: str = global_config.POSTGRES_DSN
    POSTGRES_USER: str = global_config.POSTGRES_USER
    POSTGRES_PASSWORD: str = global_config.POSTGRES_PASSWORD
    POSTGRES_HOST: str = global_config.POSTGRES_HOST
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = global_config.POSTGRES_DB

    BUS_BROKER: str = global_config.BUS_BROKER

    DATA_ROOT: str = global_config.DATA_ROOT_CONTAINER

    LOG_LEVEL: str = global_config.LOG_LEVEL


config = EvidenceBuilderConfig()
