from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, Field, field_validator
from typing import Optional, List
import os
import sys

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

# Add libs directory to PYTHONPATH for imports
sys.path.insert(0, '/app/libs')

try:
    from config import config as global_config
except ImportError:
    # Fallback for local development
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    from libs.config import config as global_config


class DatabaseSettings(BaseSettings):
    """Database configuration settings"""
    model_config = dict(env_prefix='DB_', env_file='.env')
    
    dsn: PostgresDsn = Field(
        default_factory=lambda: global_config.POSTGRES_DSN,
        description="PostgreSQL database connection string"
    )
    pool_size: int = Field(default=5, description="Database connection pool size")
    max_overflow: int = Field(default=10, description="Maximum connection pool overflow")
    timeout: int = Field(default=30, description="Database connection timeout in seconds")
    
    @field_validator('dsn', mode='before')
    @classmethod
    def validate_dsn(cls, v):
        if isinstance(v, str) and not v.startswith(('postgresql://', 'postgresql+asyncpg://')):
            raise ValueError('Database DSN must be a valid PostgreSQL connection string')
        return v


class AppSettings(BaseSettings):
    """Application configuration settings"""
    model_config = dict(env_prefix='APP_', env_file='.env')
    
    title: str = Field(default="Results API", description="Application title")
    version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="Comma-separated list of CORS origins"
    )
    log_level: str = Field(
        default_factory=lambda: global_config.LOG_LEVEL,
        description="Logging level"
    )
    port: int = Field(
        default_factory=lambda: global_config.PORT_RESULTS,
        description="API server port"
    )
    
    @field_validator('cors_origins')
    @classmethod
    def validate_cors_origins(cls, v):
        if v:
            origins = [origin.strip() for origin in v.split(',')]
            return origins
        return []
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()


class MCPSettings(BaseSettings):
    """MCP server configuration settings"""
    model_config = dict(env_prefix='MCP_', env_file='.env')
    
    enabled: bool = Field(default=True, description="Enable MCP server")
    title: str = Field(
        default="Results API MCP Server",
        description="MCP server title"
    )
    description: str = Field(
        default="MCP tools for product-video matching results",
        description="MCP server description"
    )
    mount_path: str = Field(default="/mcp", description="MCP server mount path")
    
    @field_validator('mount_path')
    @classmethod
    def validate_mount_path(cls, v):
        if not v.startswith('/'):
            v = '/' + v
        return v


class Settings(BaseSettings):
    """Main application settings"""
    model_config = dict(env_file='.env', case_sensitive=False)
    
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize nested settings if not provided
        if 'database' not in kwargs:
            self.database = DatabaseSettings()
        if 'app' not in kwargs:
            self.app = AppSettings()
        if 'mcp' not in kwargs:
            self.mcp = MCPSettings()
    
    @property
    def global_config(self):
        """Access to global configuration"""
        return global_config


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset settings singleton (useful for testing)"""
    global _settings
    _settings = None