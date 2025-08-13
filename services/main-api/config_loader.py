"""
Configuration loader for the main API service.
Loads environment variables from the service's local .env file.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class MainAPIConfig:
    ollama_host: str
    model_classify: str
    model_generate: str
    ollama_timeout: int
    industry_labels: List[str]
    default_top_amz: int
    default_top_ebay: int
    default_platforms: List[str]
    default_recency_days: int
    postgres_dsn: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: str
    postgres_db: str
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
    """Load configuration from environment file."""
    # Check if env_path is absolute, if not make it relative to the project root
    if not os.path.isabs(env_path):
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), env_path)
    
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"Environment file not found: {env_path}")
    
    kv = parse_env_file(env_path)
    
    return MainAPIConfig(
        ollama_host=kv["OLLAMA_HOST"],
        model_classify=kv["OLLAMA_MODEL_CLASSIFY"],
        model_generate=kv["OLLAMA_MODEL_GENERATE"],
        ollama_timeout=int(kv.get("OLLAMA_TIMEOUT", 60)),
        industry_labels=[x.strip() for x in kv["INDUSTRY_LABELS"].split(",")],
        default_top_amz=int(kv.get("DEFAULT_TOP_AMZ", 20)),
        default_top_ebay=int(kv.get("DEFAULT_TOP_EBAY", 20)),
        default_platforms=[x.strip() for x in kv.get("DEFAULT_PLATFORMS", "youtube,bilibili").split(",")],
        default_recency_days=int(kv.get("DEFAULT_RECENCY_DAYS", 30)),
        postgres_dsn=kv.get("POSTGRES_DSN", ""),
        postgres_user=kv.get("POSTGRES_USER", "postgres"),
        postgres_password=kv.get("POSTGRES_PASSWORD", "dev"),
        postgres_host=kv.get("POSTGRES_HOST", "postgres"),
        postgres_port=kv.get("POSTGRES_PORT", "5432"),
        postgres_db=kv.get("POSTGRES_DB", "product_video_matching"),
        bus_broker=kv.get("BUS_BROKER", "amqp://guest:guest@rabbitmq:5672/"),
    )