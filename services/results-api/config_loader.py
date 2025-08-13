"""
Configuration loader for the results API service.
Uses environment variables directly since Docker Compose loads both shared and service-specific .env files.
"""
import os
import sys
from dataclasses import dataclass

# Add project root to PYTHONPATH for local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from libs.config import config as global_config

@dataclass
class ResultsAPIConfig:
    """Configuration for the results API service"""
    
    # Database configuration (from global config)
    POSTGRES_DSN: str = global_config.POSTGRES_DSN
    POSTGRES_USER: str = global_config.POSTGRES_USER
    POSTGRES_PASSWORD: str = global_config.POSTGRES_PASSWORD
    POSTGRES_HOST: str = global_config.POSTGRES_HOST
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = global_config.POSTGRES_DB
    
    # Data storage (from global config)
    DATA_ROOT: str = global_config.DATA_ROOT
    
    # Logging (from global config)
    LOG_LEVEL: str = global_config.LOG_LEVEL

# Create config instance
config = ResultsAPIConfig()