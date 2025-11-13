"""
Centralized configuration management for the product-video matching system.
Loads environment variables from .env file and provides type-safe accessors.
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

# Helper function to get environment variable with fallback
def get_env_var(key: str, default: Optional[str] = None) -> str:
    """Get environment variable with fallback to default"""
    return os.getenv(key, default)

# Helper function to get integer environment variable
def get_env_int(key: str, default: int = 0) -> int:
    """Get integer environment variable with fallback to default"""
    value = get_env_var(key, str(default))
    try:
        return int(value)
    except ValueError:
        return default

# Helper function to get float environment variable
def get_env_float(key: str, default: float = 0.0) -> float:
    """Get float environment variable with fallback to default"""
    value = get_env_var(key, str(default))
    try:
        return float(value)
    except ValueError:
        return default

def get_env_tuple_int(key: str, default: Tuple[int, int]) -> Tuple[int, int]:
    """Get tuple of integers environment variable with fallback to default"""
    value = get_env_var(key, str(default))
    try:
        return tuple(map(int, value.strip("()").split(",")))
    except Exception:
        return default

@dataclass
class Config:
    """Centralized configuration class"""
    
    # Port Configuration
    PORT_MAIN: int = field(default_factory=lambda: get_env_int("PORT_MAIN", 8000))
    
    # Database Configuration
    POSTGRES_USER: str = field(default_factory=lambda: get_env_var("POSTGRES_USER", "postgres"))
    POSTGRES_PASSWORD: str = field(default_factory=lambda: get_env_var("POSTGRES_PASSWORD", "dev"))
    POSTGRES_DB: str = field(default_factory=lambda: get_env_var("POSTGRES_DB", "product_video_matching"))
    POSTGRES_HOST: str = field(default_factory=lambda: get_env_var("POSTGRES_HOST", "postgres"))
    POSTGRES_DSN: str = field(default_factory=lambda: get_env_var("POSTGRES_DSN") or f"postgresql://{get_env_var('POSTGRES_USER', 'postgres')}:{get_env_var('POSTGRES_PASSWORD', 'dev')}@{get_env_var('POSTGRES_HOST', 'postgres')}:{get_env_int('POSTGRES_PORT', 5432)}/{get_env_var('POSTGRES_DB', 'product_video_matching')}?sslmode=disable")
    
    # Redis
    PORT_REDIS: str = field(default_factory=lambda: get_env_int("PORT_REDIS", 6380))

    # Message Broker Configuration
    BUS_BROKER: str = field(default_factory=lambda: get_env_var("BUS_BROKER", "amqp://guest:guest@localhost:5672/"))
    
    # Data Storage
    # DATA_ROOT: str = field(default_factory=lambda: get_env_var("DATA_ROOT", "./data"))
    DATA_ROOT_CONTAINER: str = field(default_factory=lambda: get_env_var("DATA_ROOT_CONTAINER", "/app/data"))
    VIDEO_DIR: str = field(default_factory=lambda: get_env_var("VIDEO_DIR", os.path.join(get_env_var("DATA_ROOT_CONTAINER", "/app/data"), "videos")))
    
    # Vision Models
    EMBED_MODEL: str = field(default_factory=lambda: get_env_var("EMBED_MODEL", "clip-vit-b32"))
    MODEL_CACHE: str = field(default_factory=lambda: get_env_var("MODEL_CACHE", "./model_cache"))
    IMG_SIZE: Tuple[int, int] = field(default_factory=lambda: get_env_tuple_int("IMG_SIZE", (512, 512)))

    # Logging
    LOG_LEVEL: str = field(default_factory=lambda: get_env_var("LOG_LEVEL", "INFO"))
    LOG_TIMEZONE: str = field(default_factory=lambda: get_env_var("LOG_TIMEZONE", "gmt+7"))
    
    # Service URLs (for inter-service communication)
    MAIN_API_URL: str = field(default_factory=lambda: get_env_var("MAIN_API_URL", f"http://localhost:{get_env_int('PORT_MAIN', 8888)}"))
    DATA_ROOT_CONTAINER: str = field(default_factory=lambda: get_env_var("DATA_ROOT_CONTAINER", "/app/data"))
    
# Create global config instance
config = Config()
