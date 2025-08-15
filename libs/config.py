"""
Centralized configuration management for the product-video matching system.
Loads environment variables from .env file and provides type-safe accessors.
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

# Load environment variables from .env file
def load_env_file(env_path: str = None) -> Dict[str, str]:
    if env_path is None:
        # Check for test environment first
        if os.getenv("PYTEST_CURRENT_TEST"):
            env_path = "infra/pvm/.env.test"
        else:
            env_path = "infra/pvm/.env"
    """Load environment variables from .env file"""
    env_vars = {}
    env_file_path = Path(env_path)
    
    if env_file_path.exists():
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    return env_vars

# Load environment variables
env_vars = load_env_file()

# Helper function to get environment variable with fallback
def get_env_var(key: str, default: Optional[str] = None) -> str:
    """Get environment variable with fallback to default"""
    return os.getenv(key, env_vars.get(key, default))

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

@dataclass
class Config:
    """Centralized configuration class"""
    
    # Port Configuration
    PORT_MAIN: int = field(default_factory=lambda: get_env_int("PORT_MAIN", 8000))
    PORT_RESULTS: int = field(default_factory=lambda: get_env_int("PORT_RESULTS", 8080))
    
    # Database Configuration
    POSTGRES_USER: str = field(default_factory=lambda: get_env_var("POSTGRES_USER", "postgres"))
    POSTGRES_PASSWORD: str = field(default_factory=lambda: get_env_var("POSTGRES_PASSWORD", "dev"))
    POSTGRES_DB: str = field(default_factory=lambda: get_env_var("POSTGRES_DB", "product_video_matching"))
    POSTGRES_HOST: str = field(default_factory=lambda: get_env_var("POSTGRES_HOST", "localhost"))
    POSTGRES_DSN: str = field(default_factory=lambda: get_env_var("POSTGRES_DSN") or f"postgresql://{get_env_var('POSTGRES_USER', 'postgres')}:{get_env_var('POSTGRES_PASSWORD', 'dev')}@localhost:{get_env_var('PORT_POSTGRES_DB', '5432')}/{get_env_var('POSTGRES_DB', 'product_video_matching')}")
    
    # Message Broker Configuration
    BUS_BROKER: str = field(default_factory=lambda: get_env_var("BUS_BROKER", "amqp://guest:guest@localhost:5672/"))
    
    # Data Storage
    DATA_ROOT: str = field(default_factory=lambda: get_env_var("DATA_ROOT", "./data"))
    
    # Vision Models
    EMBED_MODEL: str = field(default_factory=lambda: get_env_var("EMBED_MODEL", "clip-vit-b32"))
    
    # Vector Search Configuration
    RETRIEVAL_TOPK: int = field(default_factory=lambda: get_env_int("RETRIEVAL_TOPK", 20))
    
    # Matching Thresholds
    SIM_DEEP_MIN: float = field(default_factory=lambda: get_env_float("SIM_DEEP_MIN", 0.82))
    INLIERS_MIN: float = field(default_factory=lambda: get_env_float("INLIERS_MIN", 0.35))
    MATCH_BEST_MIN: float = field(default_factory=lambda: get_env_float("MATCH_BEST_MIN", 0.88))
    MATCH_CONS_MIN: int = field(default_factory=lambda: get_env_int("MATCH_CONS_MIN", 2))
    MATCH_ACCEPT: float = field(default_factory=lambda: get_env_float("MATCH_ACCEPT", 0.80))
    
    # Logging
    LOG_LEVEL: str = field(default_factory=lambda: get_env_var("LOG_LEVEL", "INFO"))
    
    # Service URLs (for inter-service communication)
    MAIN_API_URL: str = field(default_factory=lambda: get_env_var("MAIN_API_URL", f"http://localhost:{get_env_int('PORT_MAIN', 8888)}"))
    RESULTS_API_URL: str = field(default_factory=lambda: get_env_var("RESULTS_API_URL", f"http://localhost:{get_env_int('PORT_RESULTS', 8890)}"))

# Create global config instance
config = Config()