"""
Migration configuration management for the product-video matching system.
Handles environment variable configuration and Alembic setup.
"""
import os
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MigrationConfig:
    """Configuration for database migrations"""
    
    # Database Configuration
    database_url: str
    alembic_config_path: str
    
    # Retry Configuration
    max_retries: int = 5
    retry_delay_multiplier: int = 1
    retry_delay_min: int = 1
    retry_delay_max: int = 10
    
    # Migration Configuration
    dry_run: bool = False
    verbose: bool = False
    
    @classmethod
    def from_env(cls) -> 'MigrationConfig':
        """Create configuration from environment variables"""
        # Get database URL with validation
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            # Fallback to existing config if DATABASE_URL not set
            try:
                from libs.config import config
                database_url = config.POSTGRES_DSN
                logger.info(f"Using POSTGRES_DSN from libs.config")
            except ImportError:
                raise ValueError(
                    "DATABASE_URL environment variable is required. "
                    "Set it to your database connection string."
                )
        
        # Get alembic config path with default
        alembic_config_path = os.getenv('ALEMBIC_CONFIG', 'infra/migrations/alembic.ini')
        
        # Validate alembic config file exists
        if not Path(alembic_config_path).exists():
            raise FileNotFoundError(
                f"Alembic configuration file not found: {alembic_config_path}"
            )
        
        # Get retry configuration
        max_retries = int(os.getenv('MIGRATION_MAX_RETRIES', '5'))
        retry_delay_multiplier = int(os.getenv('MIGRATION_RETRY_MULTIPLIER', '1'))
        retry_delay_min = int(os.getenv('MIGRATION_RETRY_MIN_DELAY', '1'))
        retry_delay_max = int(os.getenv('MIGRATION_RETRY_MAX_DELAY', '10'))
        
        # Get migration options
        dry_run = os.getenv('MIGRATION_DRY_RUN', 'false').lower() == 'true'
        verbose = os.getenv('MIGRATION_VERBOSE', 'false').lower() == 'true'
        
        return cls(
            database_url=database_url,
            alembic_config_path=alembic_config_path,
            max_retries=max_retries,
            retry_delay_multiplier=retry_delay_multiplier,
            retry_delay_min=retry_delay_min,
            retry_delay_max=retry_delay_max,
            dry_run=dry_run,
            verbose=verbose
        )
    
    def validate(self) -> None:
        """Validate configuration"""
        if not self.database_url:
            raise ValueError("Database URL is required")
        
        if not self.alembic_config_path:
            raise ValueError("Alembic config path is required")
        
        if not Path(self.alembic_config_path).exists():
            raise FileNotFoundError(f"Alembic config file not found: {self.alembic_config_path}")
        
        if self.max_retries < 1:
            raise ValueError("Max retries must be at least 1")
        
        if self.retry_delay_min < 0:
            raise ValueError("Min retry delay cannot be negative")
        
        if self.retry_delay_max < self.retry_delay_min:
            raise ValueError("Max retry delay must be >= min retry delay")
    
    def get_database_url_for_alembic(self) -> str:
        """Get database URL formatted for Alembic"""
        # If the URL already contains the alembic config, use it as-is
        if 'postgresql://' in self.database_url or 'mysql://' in self.database_url:
            return self.database_url
        
        # Otherwise, assume it's a simple URL that needs to be formatted
        return self.database_url