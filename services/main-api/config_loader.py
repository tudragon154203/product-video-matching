"""
Configuration loader for the main API service.
Loads environment variables from the service's local .env file and combines them with global configuration.
"""
import os
import sys
# Add libs to the path to import config
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "libs"))
from dataclasses import dataclass
from pathlib import Path
from typing import List
from config import Config as GlobalConfig, get_env_var, get_env_int


@dataclass
class MainAPIConfig:
    # Ollama configuration
    ollama_host: str
    model_classify: str
    model_generate: str
    ollama_timeout: int
    
    # Industry labels
    industry_labels: List[str]
    
    # Defaults
    default_top_amz: int
    default_top_ebay: int
    default_platforms: List[str]
    default_recency_days: int
    
    # Database configuration (from global config)
    postgres_dsn: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: str
    postgres_db: str
    
    # Message broker configuration (from global config)
    bus_broker: str


def parse_env_file(env_path: str) -> dict:
    """Parse environment file and return key-value pairs."""
    kv = {}
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                kv[key.strip()] = value.strip().strip('"').strip("'")  # Strip quotes
    return kv


def load_env(env_path: str = "services/main-api/.env") -> MainAPIConfig:
    """Load configuration from environment file and global config."""
    # Check if env_path is absolute, if not make it relative to the project root
    if not os.path.isabs(env_path):
        # Try to find the .env file in the current directory first
        if os.path.exists(".env"):
            env_path = ".env"
        else:
            # Fallback to the original path calculation
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), env_path)
    
    # Load the global configuration
    global_config = GlobalConfig()
    
    # Load service-specific environment variables
    kv = {}
    if os.path.exists(env_path):
        kv = parse_env_file(env_path)
    
    return MainAPIConfig(
        # Ollama configuration
        ollama_host=kv.get("OLLAMA_HOST", "http://localhost:11434"),
        model_classify=kv.get("OLLAMA_MODEL_CLASSIFY", "qwen3:4b-instruct"),
        model_generate=kv.get("OLLAMA_MODEL_GENERATE", "qwen3:4b-instruct"),
        ollama_timeout=int(kv.get("OLLAMA_TIMEOUT", 60)),
        
        # Industry labels
        industry_labels=[x.strip() for x in kv.get("INDUSTRY_LABELS", "fashion,beauty_personal_care,books,electronics,home_garden,sports_outdoors,baby_products,pet_supplies,toys_games,automotive,office_products,business_industrial,collectibles_art,jewelry_watches,other").split(",")],
        
        # Defaults
        default_top_amz=int(kv.get("DEFAULT_TOP_AMZ", 20)),
        default_top_ebay=int(kv.get("DEFAULT_TOP_EBAY", 20)),
        default_platforms=[x.strip() for x in kv.get("DEFAULT_PLATFORMS", "youtube,bilibili").split(",")],
        default_recency_days=int(kv.get("DEFAULT_RECENCY_DAYS", 30)),
        
        # Database configuration (from global config)
        postgres_dsn=get_env_var("POSTGRES_DSN", global_config.POSTGRES_DSN),
        postgres_user=get_env_var("POSTGRES_USER", global_config.POSTGRES_USER),
        postgres_password=get_env_var("POSTGRES_PASSWORD", global_config.POSTGRES_PASSWORD),
        postgres_host=get_env_var("POSTGRES_HOST", global_config.POSTGRES_HOST),
        postgres_port=get_env_var("POSTGRES_PORT", "5432"),
        postgres_db=get_env_var("POSTGRES_DB", global_config.POSTGRES_DB),
        
        # Message broker configuration (from global config)
        bus_broker=get_env_var("BUS_BROKER", global_config.BUS_BROKER),
    )