"""
Configuration loader for the matcher service.
Uses environment variables directly since Docker Compose loads both shared and service-specific .env files.
"""
import os
import sys
from dataclasses import dataclass

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

@dataclass
class MatcherConfig:
    """Configuration for the matcher service"""
    
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
    DATA_ROOT: str = global_config.DATA_ROOT
    
    # Matching parameters (from global config)
    RETRIEVAL_TOPK: int = global_config.RETRIEVAL_TOPK
    SIM_DEEP_MIN: float = global_config.SIM_DEEP_MIN
    INLIERS_MIN: float = global_config.INLIERS_MIN
    MATCH_BEST_MIN: float = global_config.MATCH_BEST_MIN
    MATCH_CONS_MIN: int = global_config.MATCH_CONS_MIN
    MATCH_ACCEPT: float = global_config.MATCH_ACCEPT
    
    # Logging (from global config)
    LOG_LEVEL: str = global_config.LOG_LEVEL

# Create config instance
config = MatcherConfig()