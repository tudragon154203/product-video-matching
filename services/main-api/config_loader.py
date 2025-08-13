"""
Simplified configuration loader for the main API service.
Uses environment variables directly since Docker Compose loads both shared and service-specific .env files.
"""
import os
import sys
from dataclasses import dataclass, field
from typing import List

# Add libs directory to PYTHONPATH for imports
sys.path.insert(0, '/app/libs')

try:
    from config import config as global_config
except ImportError:
    # Fallback for local development
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from libs.config import config as global_config

@dataclass
class MainAPIConfig:
    # Ollama configuration
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
    OLLAMA_MODEL_CLASSIFY: str = os.getenv("OLLAMA_MODEL_CLASSIFY", "qwen3:4b-instruct")
    OLLAMA_MODEL_GENERATE: str = os.getenv("OLLAMA_MODEL_GENERATE", "qwen3:4b-instruct")
    
    # LLM configuration
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "60"))
    
    # Gemini configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # Industry labels
    INDUSTRY_LABELS: List[str] = field(
        default_factory=lambda: os.getenv(
            "INDUSTRY_LABELS",
            "fashion,beauty_personal_care,books,electronics,home_garden,sports_outdoors,baby_products,pet_supplies,toys_games,automotive,office_products,business_industrial,collectibles_art,jewelry_watches,other"
        ).split(",")
    )
    
    # Defaults
    DEFAULT_TOP_AMZ: int = int(os.getenv("DEFAULT_TOP_AMZ", "20"))
    DEFAULT_TOP_EBAY: int = int(os.getenv("DEFAULT_TOP_EBAY", "20"))
    DEFAULT_PLATFORMS: List[str] = field(
        default_factory=lambda: os.getenv("DEFAULT_PLATFORMS", "youtube,bilibili").split(",")
    )
    DEFAULT_RECENCY_DAYS: int = int(os.getenv("DEFAULT_RECENCY_DAYS", "30"))
    
    # Database configuration (from global config)
    POSTGRES_DSN: str = global_config.POSTGRES_DSN
    POSTGRES_USER: str = global_config.POSTGRES_USER
    POSTGRES_PASSWORD: str = global_config.POSTGRES_PASSWORD
    POSTGRES_HOST: str = global_config.POSTGRES_HOST
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = global_config.POSTGRES_DB
    
    # Message broker configuration (from global config)
    BUS_BROKER: str = global_config.BUS_BROKER

# Create config instance
config = MainAPIConfig()