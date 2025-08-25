"""
Dependency injection module for main-api service.
Provides shared database and message broker instances.
"""
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from config_loader import config

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
        raise RuntimeError("Dependencies not initialized. Call init_dependencies() first.")
    return _db_instance

def get_broker() -> MessageBroker:
    """Get shared message broker instance"""
    if _broker_instance is None:
        raise RuntimeError("Dependencies not initialized. Call init_dependencies() first.")
    return _broker_instance