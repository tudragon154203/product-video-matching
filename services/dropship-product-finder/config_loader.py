"""
Configuration loader for the catalog collector service.
Uses environment variables directly since Docker Compose loads both shared and service-specific .env files.
"""
import os
import sys
from pathlib import Path
from dataclasses import dataclass

# Add libs directory to PYTHONPATH for imports
sys.path.insert(0, '/app/libs')

def load_service_env():
    """Load service-specific environment variables"""
    # Try to load service-specific .env file
    service_env_path = Path(__file__).parent / '.env'
    if service_env_path.exists():
        with open(service_env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')  # Remove quotes
                    os.environ[key] = value
                    print(f"Loaded environment variable: {key}")

# Load service-specific environment variables
load_service_env()

try:
    from config import config as global_config
except ImportError:
    # Fallback for local development
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from libs.config import config as global_config

@dataclass
class DropshipProductFinderConfig:
    """Configuration for the catalog collector service"""
    
    # eBay API configuration
    EBAY_CLIENT_ID: str = os.getenv("EBAY_CLIENT_ID", "")
    EBAY_CLIENT_SECRET: str = os.getenv("EBAY_CLIENT_SECRET", "")
    EBAY_MARKETPLACES: str = os.getenv("EBAY_MARKETPLACES", "EBAY_US")
    EBAY_ENVIRONMENT: str = os.getenv("EBAY_ENVIRONMENT", "sandbox")
    EBAY_SCOPES: str = os.getenv("EBAY_SCOPES", "https://api.ebay.com/oauth/api_scope")
    
    # Redis configuration for token storage
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = os.getenv("REDIS_PORT", 6379)
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
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
    
    # Logging (from global config)
    LOG_LEVEL: str = global_config.LOG_LEVEL
    
    @property
    def EBAY_TOKEN_URL(self) -> str:
        """Get the appropriate token URL based on environment"""
        if self.EBAY_ENVIRONMENT == "sandbox":
            return "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
        return "https://api.ebay.com/identity/v1/oauth2/token"
    
    @property
    def REDIS_URL(self) -> str:
        """Get Redis connection URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

# Create config instance
config = DropshipProductFinderConfig()