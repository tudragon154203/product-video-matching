"""Configuration loader for the product finder service.

Uses environment variables directly because Docker Compose loads both
shared and service-specific `.env` files.
"""

import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# Add libs directory to PYTHONPATH for imports
sys.path.insert(0, "/app/libs")

try:
    from config import config as global_config
except ImportError:
    # Fallback for local development
    sys.path.append(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    from libs.config import config as global_config


@dataclass
class DropshipProductFinderConfig:
    """Configuration for the product finder service."""

    # eBay API configuration
    EBAY_SANDBOX_CLIENT_ID: str = os.getenv("EBAY_SANDBOX_CLIENT_ID", "")
    EBAY_PRODUCTION_CLIENT_ID: str = os.getenv("EBAY_PRODUCTION_CLIENT_ID", "")
    EBAY_SANDBOX_CLIENT_SECRET: str = os.getenv("EBAY_SANDBOX_CLIENT_SECRET", "")
    EBAY_PRODUCTION_CLIENT_SECRET: str = os.getenv("EBAY_PRODUCTION_CLIENT_SECRET", "")
    EBAY_MARKETPLACES: str = os.getenv("EBAY_MARKETPLACES", "EBAY_US")
    EBAY_ENVIRONMENT: str = os.getenv("EBAY_ENVIRONMENT", "sandbox")
    EBAY_SCOPES: str = os.getenv("EBAY_SCOPES", "https://api.ebay.com/oauth/api_scope")

    # Mock configuration - set to True to use mock product finders instead of real APIs
    USE_MOCK_FINDERS: bool = os.getenv("USE_MOCK_FINDERS", "true").lower() == "true"

    # Redis configuration for token storage
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
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
    DATA_ROOT: str = global_config.DATA_ROOT_CONTAINER

    # Logging (from global config)
    LOG_LEVEL: str = global_config.LOG_LEVEL

    # eBay Browse API configuration
    TIMEOUT_SECS_BROWSE: float = float(os.getenv("BROWSE_TIMEOUT_SECS", 30.0))
    MAX_RETRIES_BROWSE: int = int(os.getenv("BROWSE_MAX_RETRIES", 2))
    BACKOFF_BASE_BROWSE: float = float(os.getenv("BROWSE_BACKOFF_BASE", 1.5))

    # Performance tuning
    BROWSE_CONCURRENCY: int = int(os.getenv("BROWSE_CONCURRENCY", "4"))
    ITEM_CONCURRENCY: int = int(os.getenv("ITEM_CONCURRENCY", "4"))
    IMAGE_DOWNLOAD_TIMEOUT_SECS: float = float(os.getenv("IMAGE_DOWNLOAD_TIMEOUT_SECS", 30.0))

    @property
    def EBAY_CLIENT_ID(self) -> str:
        """Get the appropriate client ID based on environment"""
        if self.EBAY_ENVIRONMENT == "production":
            return self.EBAY_PRODUCTION_CLIENT_ID
        return self.EBAY_SANDBOX_CLIENT_ID

    @property
    def EBAY_CLIENT_SECRET(self) -> str:
        """Get the appropriate client secret based on environment"""
        if self.EBAY_ENVIRONMENT == "production":
            return self.EBAY_PRODUCTION_CLIENT_SECRET
        return self.EBAY_SANDBOX_CLIENT_SECRET

    @property
    def EBAY_BROWSE_BASE(self) -> str:
        """Get the appropriate Browse API base URL based on environment"""
        if self.EBAY_ENVIRONMENT == "production":
            return "https://api.ebay.com/buy/browse/v1"
        return "https://api.sandbox.ebay.com/buy/browse/v1"

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
