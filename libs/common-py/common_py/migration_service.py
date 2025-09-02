"""
Main migration service with comprehensive error handling and logging integration.
"""
import sys
import signal
import traceback
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from enum import Enum

from .migration_config import MigrationConfig
from .migration_executor import MigrationExecutor
from .logging_config import configure_logging

logger = configure_logging("common-py:migration_service")


class MigrationAction(Enum):
    """Available migration actions"""
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"
    STATUS = "status"
    LIST = "list"
    GENERATE = "generate"


class MigrationError(Exception):
    """Base migration error"""
    pass


class MigrationConfigurationError(MigrationError):
    """Migration configuration error"""
    pass


class MigrationConnectionError(MigrationError):
    """Migration connection error"""
    pass


class MigrationExecutionError(MigrationError):
    """Migration execution error"""
    pass


class MigrationService:
    """Main migration service with comprehensive error handling"""
    
    def __init__(self, service_name: str = "migration_service"):
        self.service_name = service_name
        self.config: Optional[MigrationConfig] = None
        self.executor: Optional[MigrationExecutor] = None
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.cleanup()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def initialize(self, config: Optional[MigrationConfig] = None) -> None:
        """Initialize the migration service"""
        try:
            # Load configuration
            if config is None:
                self.config = MigrationConfig.from_env()
            else:
                self.config = config
            
            # Validate configuration
            self.config.validate()
            
            # Setup logging for this module using standardized name
            configure_logging("common-py:migration_service", self.config.verbose and "DEBUG" or "INFO")
            
            # Create executor
            self.executor = MigrationExecutor(self.config)
            
            logger.info(f"Migration service initialized for {self.service_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize migration service: {str(e)}")
            logger.debug(traceback.format_exc())
            raise MigrationConfigurationError(f"Service initialization failed: {str(e)}")
    
    def _validate_initialized(self) -> None:
        """Validate that the service is properly initialized"""
        if self.config is None:
            raise MigrationConfigurationError("Service not initialized. Call initialize() first.")
        
        if self.executor is None:
            raise MigrationConfigurationError("Migration executor not available.")
    
    def _handle_migration_error(self, error: Exception, action: str) -> None:
        """Handle migration errors with appropriate logging"""
        error_type = type(error).__name__
        
        if isinstance(error, MigrationConfigurationError):
            logger.error(f"Configuration error during {action}: {str(error)}")
        elif isinstance(error, MigrationConnectionError):
            logger.error(f"Connection error during {action}: {str(error)}")
        elif isinstance(error, MigrationExecutionError):
            logger.error(f"Execution error during {action}: {str(error)}")
        else:
            logger.error(f"Unexpected error during {action}: {str(error)}")
            logger.debug(traceback.format_exc())
        
        # Re-raise with additional context
        raise MigrationExecutionError(f"{action} failed: {str(error)}") from error
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status"""
        try:
            self._validate_initialized()
            
            logger.info("Checking migration status...")
            
            status = self.executor.check_migration_status()
            
            logger.info("Migration status retrieved successfully")
            return status
            
        except Exception as e:
            self._handle_migration_error(e, "status check")
    
    def run_migration(self, action: MigrationAction, **kwargs) -> Dict[str, Any]:
        """Run migration with specified action"""
        try:
            self._validate_initialized()
            
            action_name = action.value.upper()
            logger.info(f"Starting migration action: {action_name}")
            
            # Execute migration
            result = None
            start_time = datetime.now()
            
            if action == MigrationAction.UPGRADE:
                success = self.executor.upgrade_to_head()
                result = {"success": success, "action": "upgrade"}
                
            elif action == MigrationAction.DOWNGRADE:
                success = self.executor.downgrade_to_base()
                result = {"success": success, "action": "downgrade"}
                
            elif action == MigrationAction.STATUS:
                result = self.get_migration_status()
                
            elif action == MigrationAction.LIST:
                result = self.executor.list_migrations()
                
            elif action == MigrationAction.GENERATE:
                message = kwargs.get("message", "auto-generated migration")
                autogenerate = kwargs.get("autogenerate", True)
                success = self.executor.generate_revision(message, autogenerate)
                result = {"success": success, "action": "generate", "message": message}
            
            else:
                raise MigrationExecutionError(f"Unknown migration action: {action}")
            
            # Calculate duration
            duration = datetime.now() - start_time
            result["duration_seconds"] = duration.total_seconds()
            result["timestamp"] = datetime.now().isoformat()
            
            # Log completion
            if result.get("success", False):
                logger.info(f"Migration action {action_name} completed successfully in {duration.total_seconds():.2f}s")
            else:
                logger.error(f"Migration action {action_name} failed")
            
            return result
            
        except Exception as e:
            self._handle_migration_error(e, f"migration {action.value}")
    
    def run_upgrade(self) -> Dict[str, Any]:
        """Run database upgrade to latest version"""
        return self.run_migration(MigrationAction.UPGRADE)
    
    def run_downgrade(self) -> Dict[str, Any]:
        """Run database downgrade to base version"""
        return self.run_migration(MigrationAction.DOWNGRADE)
    
    def list_migrations(self) -> Dict[str, Any]:
        """List available migrations"""
        return self.run_migration(MigrationAction.LIST)
    
    def generate_migration(self, message: str, autogenerate: bool = True) -> Dict[str, Any]:
        """Generate new migration revision"""
        return self.run_migration(
            MigrationAction.GENERATE,
            message=message,
            autogenerate=autogenerate
        )
    
    def validate_environment(self) -> Dict[str, Any]:
        """Validate migration environment"""
        try:
            self._validate_initialized()
            
            validation_results = {
                "timestamp": datetime.now().isoformat(),
                "config_valid": True,
                "connection_valid": False,
                "alembic_config_valid": False,
                "prerequisites_met": False
            }
            
            # Validate configuration
            try:
                self.config.validate()
                validation_results["config_valid"] = True
            except Exception as e:
                validation_results["config_valid"] = False
                validation_results["config_error"] = str(e)
            
            # Test database connection
            try:
                validation_results["connection_valid"] = self.executor.connection_manager.test_connection()
            except Exception as e:
                validation_results["connection_error"] = str(e)
            
            # Validate Alembic configuration
            try:
                validation_results["alembic_config_valid"] = self.executor.alembic_cfg is not None
                if validation_results["alembic_config_valid"]:
                    validation_results["alembic_config_path"] = self.config.alembic_config_path
            except Exception as e:
                validation_results["alembic_config_error"] = str(e)
            
            # Check prerequisites
            validation_results["prerequisites_met"] = all([
                validation_results["config_valid"],
                validation_results["connection_valid"],
                validation_results["alembic_config_valid"]
            ])
            
            # Log results
            if validation_results["prerequisites_met"]:
                logger.info("Environment validation passed")
            else:
                logger.warning("Environment validation failed")
                for key, value in validation_results.items():
                    if key.endswith("_error") and value:
                        logger.error(f"{key}: {value}")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Environment validation failed: {str(e)}")
            return {
                "timestamp": datetime.now().isoformat(),
                "valid": False,
                "error": str(e)
            }
    
    def cleanup(self) -> None:
        """Clean up resources"""
        try:
            if self.executor:
                self.executor.close()
                logger.info("Migration executor cleaned up")
            
            logger.info("Migration service cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()


def create_migration_service(service_name: str = "migration_service") -> MigrationService:
    """Factory function to create migration service"""
    service = MigrationService(service_name)
    service.initialize()
    return service
