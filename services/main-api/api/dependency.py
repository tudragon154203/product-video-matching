"""
Dependency injection module for main-api service.
Provides shared database and message broker instances.
"""
from common_py.crud.product_image_crud import ProductImageCRUD
from common_py.crud.product_crud import ProductCRUD
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from config_loader import config
from fastapi import Depends  # Add this import
from services.job.job_service import JobService  # Add this import

# Global instances (will be initialized on startup)
_db_instance: DatabaseManager = None
_broker_instance: MessageBroker = None


def init_dependencies():
    """Initialize shared database and broker instances"""
    global _db_instance, _broker_instance

    _db_instance = DatabaseManager(config.POSTGRES_DSN)
    _broker_instance = MessageBroker(config.BUS_BROKER)


def get_db() -> DatabaseManager:
    """Get shared database instance"""
    if _db_instance is None:
        raise RuntimeError(
            "Dependencies not initialized. Call init_dependencies() first.")
    return _db_instance


def get_broker() -> MessageBroker:
    """Get shared message broker instance"""
    if _broker_instance is None:
        raise RuntimeError(
            "Dependencies not initialized. Call init_dependencies() first.")
    return _broker_instance


def get_job_service(db: DatabaseManager = Depends(get_db), broker: MessageBroker = Depends(get_broker)) -> JobService:
    # Import here to avoid circular dependency
    from services.job.job_service import JobService
    return JobService(db, broker)


def get_product_image_crud(db: DatabaseManager = Depends(get_db)) -> ProductImageCRUD:
    return ProductImageCRUD(db)


def get_product_crud(db: DatabaseManager = Depends(get_db)) -> ProductCRUD:
    return ProductCRUD(db)
