from typing import AsyncGenerator, Annotated, Optional
from fastapi import Depends, Request
from contextlib import asynccontextmanager
import logging

from common_py.database import DatabaseManager
from core.config import get_settings, Settings
from core.exceptions import DatabaseError, ServiceError

logger = logging.getLogger(__name__)


class DatabaseManagerSingleton:
    """Singleton database manager for the application"""
    _instance: Optional[DatabaseManager] = None
    _connected: bool = False

    @classmethod
    async def get_instance(cls) -> DatabaseManager:
        """Get or create database manager instance"""
        if cls._instance is None:
            settings = get_settings()
            cls._instance = DatabaseManager(str(settings.database.dsn))
            logger.info("Database manager instance created")
        
        if not cls._connected:
            try:
                await cls._instance.connect()
                cls._connected = True
                logger.info("Database connection established")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise DatabaseError(f"Failed to connect to database: {e}")
        
        return cls._instance

    @classmethod
    async def close_connection(cls) -> None:
        """Close database connection"""
        if cls._instance and cls._connected:
            try:
                await cls._instance.disconnect()
                cls._connected = False
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")

    @classmethod
    @asynccontextmanager
    async def get_db_context(cls) -> AsyncGenerator[DatabaseManager, None]:
        """Get database manager with context management"""
        db = await cls.get_instance()
        try:
            yield db
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise DatabaseError(f"Database operation failed: {e}")


async def get_settings_dependency() -> Settings:
    """Dependency to get application settings"""
    return get_settings()


async def get_db_session() -> DatabaseManager:
    """Dependency to get database session"""
    return await DatabaseManagerSingleton.get_instance()


async def get_results_service(
    db: DatabaseManager = Depends(get_db_session)
) -> "ResultsService":
    """Dependency to get results service instance"""
    try:
        # Import here to avoid circular imports
        from services.results_service import ResultsService
        return ResultsService(db)
    except Exception as e:
        logger.error(f"Failed to create results service: {e}")
        raise ServiceError(f"Failed to create results service: {e}")


# Type annotations for dependency injection
DatabaseDependency = Annotated[DatabaseManager, Depends(get_db_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings_dependency)]
ResultsServiceDependency = Annotated["ResultsService", Depends(get_results_service)]


# Lifecycle management functions
async def startup_dependencies() -> None:
    """Initialize dependencies on application startup"""
    try:
        # Initialize database connection
        await DatabaseManagerSingleton.get_instance()
        logger.info("Dependencies initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize dependencies: {e}")
        raise


async def shutdown_dependencies() -> None:
    """Clean up dependencies on application shutdown"""
    try:
        await DatabaseManagerSingleton.close_connection()
        logger.info("Dependencies cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during dependency cleanup: {e}")