"""
Simplified configuration loader for the main API service.
Uses environment variables directly since Docker Compose loads both shared and service-specific .env files.
"""
import os
from dataclasses import dataclass
from typing import List
from libs.config import config as global_config

@dataclass
class MainAPIConfig:
    # Ollama configuration
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
    model_classify: str = os.getenv("OLLAMA_MODEL_CLASSIFY", "qwen3:4b-instruct")
    model_generate: str = os.getenv("OLLAMA_MODEL_GENERATE", "qwen3:4b-instruct")
    ollama_timeout: int = int(os.getenv("OLLAMA_TIMEOUT", "60"))
    
    # Industry labels
    industry_labels: List[str] = os.getenv(
        "INDUSTRY_LABELS",
        "fashion,beauty_personal_care,books,electronics,home_garden,sports_outdoors,baby_products,pet_supplies,toys_games,automotive,office_products,business_industrial,collectibles_art,jewelry_watches,other"
    ).split(",")
    
    # Defaults
    default_top_amz: int = int(os.getenv("DEFAULT_TOP_AMZ", "20"))
    default_top_ebay: int = int(os.getenv("DEFAULT_TOP_EBAY", "20"))
    default_platforms: List[str] = os.getenv("DEFAULT_PLATFORMS", "youtube,bilibili").split(",")
    default_recency_days: int = int(os.getenv("DEFAULT_RECENCY_DAYS", "30"))
    
    # Database configuration (from global config)
    postgres_dsn: str = global_config.POSTGRES_DSN
    postgres_user: str = global_config.POSTGRES_USER
    postgres_password: str = global_config.POSTGRES_PASSWORD
    postgres_host: str = global_config.POSTGRES_HOST
    postgres_port: str = os.getenv("POSTGRES_PORT", "5432")
    postgres_db: str = global_config.POSTGRES_DB
    
    # Message broker configuration (from global config)
    bus_broker: str = global_config.BUS_BROKER

# Create config instance
config = MainAPIConfig()