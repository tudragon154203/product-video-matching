"""
Database connection management with retry logic for migrations.
"""
import time
from typing import Optional, Any
from contextlib import contextmanager
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.exc import OperationalError, DisconnectionError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .migration_config import MigrationConfig
from .logging_config import configure_logging

logger = configure_logging("common-py:migration_connection")


class MigrationConnectionManager:
    """Manages database connections with retry logic for migrations"""
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.engine: Optional[Engine] = None
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate configuration"""
        self.config.validate()
    
    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with connection pooling"""
        try:
            logger.info(f"Creating database engine for: {self.config.database_url}")
            
            # Create engine with connection pooling
            engine = create_engine(
                self.config.database_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,  # Test connections before use
                pool_recycle=3600,   # Recycle connections after 1 hour
                echo=self.config.verbose  # Log SQL if verbose mode
            )
            
            return engine
            
        except Exception as e:
            logger.error(f"Failed to create database engine: {str(e)}")
            raise
    
    def _get_connection(self) -> Any:
        """Get database connection with retry logic"""
        if self.engine is None:
            self.engine = self._create_engine()
        
        last_exception = None
        for attempt in range(self.config.max_retries):
            try:
                connection = self.engine.connect()
                logger.info("Database connection established successfully")
                return connection
                
            except OperationalError as e:
                last_exception = e
                logger.warning(f"Database connection failed (attempt {attempt + 1}/{self.config.max_retries}): {str(e)}")
                if attempt < self.config.max_retries - 1:
                    delay = min(
                        self.config.retry_delay_min * (self.config.retry_delay_multiplier ** attempt),
                        self.config.retry_delay_max
                    )
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error("Max retry attempts reached for database connection")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error establishing database connection: {str(e)}")
                raise
        
        if last_exception:
            raise last_exception
    
    def _get_retry_count(self) -> int:
        """Get current retry count (simplified version)"""
        # This is a simplified implementation
        # In a real scenario, you'd track the actual retry count
        return 1
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        connection = None
        try:
            connection = self._get_connection()
            yield connection
            
        except Exception as e:
            logger.error(f"Failed to get database connection: {str(e)}")
            raise
            
        finally:
            if connection:
                connection.close()
                logger.debug("Database connection closed")
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                # Simple test query
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                logger.info("Database connection test successful")
                return True
                
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False
    
    def get_engine(self) -> Engine:
        """Get SQLAlchemy engine"""
        if self.engine is None:
            self.engine = self._create_engine()
        return self.engine
    
    def close(self) -> None:
        """Close database engine"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database engine disposed")
            self.engine = None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
