from pydantic_settings import BaseSettings
from pydantic import PostgresDsn
from typing import Optional


class DatabaseSettings(BaseSettings):
    model_config = dict(env_prefix='DB_', env_file='.env')
    
    dsn: PostgresDsn = "postgresql://localhost:5435/postgres"
    pool_size: int = 5
    max_overflow: int = 10
    timeout: int = 30


class AppSettings(BaseSettings):
    model_config = dict(env_prefix='APP_', env_file='.env')
    
    title: str = "Results API"
    version: str = "1.0.0"
    debug: bool = False
    cors_origins: str = "http://localhost:3000,http://localhost:8080"


class Settings(BaseSettings):
    database: DatabaseSettings
    app: AppSettings


def get_settings() -> Settings:
    return Settings()