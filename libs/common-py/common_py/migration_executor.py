"""
Migration executor with version tracking and idempotent operations.
"""
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from alembic import command, config
from alembic.runtime.migration import MigrationContext
from alembic.runtime.environment import EnvironmentContext
import json

from .migration_config import MigrationConfig
from .migration_connection import MigrationConnectionManager
from .logging_config import configure_logging

logger = configure_logging("common-py:migration_executor")


class MigrationExecutor:
    """Handles migration execution with version tracking and idempotency"""
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.connection_manager = MigrationConnectionManager(config)
        self.alembic_cfg: Optional[config.Config] = None
        self._setup_alembic_config()
    
    def _setup_alembic_config(self) -> None:
        """Setup Alembic configuration"""
        try:
            # Create Alembic config object
            self.alembic_cfg = config.Config(
                self.config.alembic_config_path,
                ini_section="alembic"
            )
            
            # Override database URL if needed
            if self.config.database_url:
                self.alembic_cfg.set_main_option("sqlalchemy.url", self.config.database_url)
            
            logger.info(f"Alembic configuration loaded from: {self.config.alembic_config_path}")
            
        except Exception as e:
            logger.error(f"Failed to setup Alembic configuration: {str(e)}")
            raise
    
    def _get_current_revision(self) -> Optional[str]:
        """Get current database revision"""
        try:
            with self.connection_manager.get_connection() as conn:
                context = MigrationContext.configure(conn)
                return context.get_current_revision()
                
        except Exception as e:
            logger.warning(f"Could not get current revision: {str(e)}")
            return None
    
    def _get_target_revision(self) -> str:
        """Get target revision (head for latest)"""
        return "head"
    
    def _log_migration_start(self, current_rev: Optional[str], target_rev: str) -> None:
        """Log migration start information"""
        logger.info("=" * 60)
        logger.info("DATABASE MIGRATION STARTED")
        logger.info("=" * 60)
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info(f"Database URL: {self.config.database_url}")
        logger.info(f"Alembic Config: {self.config.alembic_config_path}")
        logger.info(f"Current Revision: {current_rev or 'None'}")
        logger.info(f"Target Revision: {target_rev}")
        logger.info(f"Dry Run: {self.config.dry_run}")
        logger.info(f"Verbose: {self.config.verbose}")
        logger.info(f"Max Retries: {self.config.max_retries}")
        logger.info("=" * 60)
    
    def _log_migration_success(self, current_rev: Optional[str], target_rev: str) -> None:
        """Log migration success"""
        logger.info("=" * 60)
        logger.info("DATABASE MIGRATION COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info(f"Final Revision: {current_rev}")
        logger.info(f"Target Revision: {target_rev}")
        logger.info(f"Duration: {datetime.now().isoformat()}")
        logger.info("=" * 60)
    
    def _log_migration_failure(self, error: Exception) -> None:
        """Log migration failure"""
        logger.error("=" * 60)
        logger.error("DATABASE MIGRATION FAILED")
        logger.error("=" * 60)
        logger.error(f"Error: {str(error)}")
        logger.error(f"Timestamp: {datetime.now().isoformat()}")
        logger.error("=" * 60)
    
    def _validate_migration_prerequisites(self) -> bool:
        """Validate migration prerequisites"""
        try:
            # Test database connection
            if not self.connection_manager.test_connection():
                logger.error("Database connection test failed")
                return False
            
            # Check if alembic versions directory exists
            versions_dir = Path(self.config.alembic_config_path).parent / "versions"
            if not versions_dir.exists():
                logger.error(f"Alembic versions directory not found: {versions_dir}")
                return False
            
            # List available migrations
            migrations = self._list_available_migrations()
            if not migrations:
                logger.warning("No migrations found in versions directory")
            
            logger.info(f"Found {len(migrations)} migration(s)")
            for migration in migrations:
                logger.info(f"  - {migration}")
            
            return True
            
        except Exception as e:
            logger.error(f"Migration validation failed: {str(e)}")
            return False
    
    def _list_available_migrations(self) -> List[str]:
        """List available migration files"""
        try:
            versions_dir = Path(self.config.alembic_config_path).parent / "versions"
            if not versions_dir.exists():
                return []
            
            migrations = []
            for file_path in versions_dir.glob("*.py"):
                if file_path.name != "__init__.py":
                    migrations.append(file_path.stem)
            
            return sorted(migrations)
            
        except Exception as e:
            logger.error(f"Failed to list migrations: {str(e)}")
            return []
    
    def _execute_migration_command(self, command_name: str, *args, **kwargs) -> Any:
        """Execute Alembic command with error handling"""
        try:
            if self.config.dry_run:
                logger.info(f"DRY RUN: Would execute alembic {command_name}")
                return None
            
            # Add project root to Python path for imports
            project_root = Path(__file__).parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            # Change working directory to migrations directory for Alembic
            migrations_dir = Path(self.config.alembic_config_path).parent
            original_cwd = os.getcwd()
            os.chdir(migrations_dir)
            logger.debug(f"Changed working directory to: {migrations_dir}")
            
            try:
                # Execute the command
                command_func = getattr(command, command_name)
                return command_func(self.alembic_cfg, *args, **kwargs)
            finally:
                # Restore original working directory
                os.chdir(original_cwd)
                logger.debug(f"Restored working directory to: {original_cwd}")
            
        except Exception as e:
            logger.error(f"Alembic command '{command_name}' failed: {str(e)}")
            raise
    
    def check_migration_status(self) -> Dict[str, Any]:
        """Check current migration status"""
        try:
            current_rev = self._get_current_revision()
            target_rev = self._get_target_revision()
            available_migrations = self._list_available_migrations()
            
            status = {
                "database_url": self.config.database_url,
                "current_revision": current_rev,
                "target_revision": target_rev,
                "available_migrations": available_migrations,
                "migration_needed": current_rev != target_rev,
                "dry_run": self.config.dry_run,
                "timestamp": datetime.now().isoformat()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to check migration status: {str(e)}")
            raise
    
    def upgrade_to_head(self) -> bool:
        """Upgrade database to latest migration"""
        try:
            # Validate prerequisites
            if not self._validate_migration_prerequisites():
                logger.error("Migration prerequisites not met")
                return False
            
            # Get current and target revisions
            current_rev = self._get_current_revision()
            target_rev = self._get_target_revision()
            
            # Log start
            self._log_migration_start(current_rev, target_rev)
            
            # Check if upgrade is needed
            if current_rev == target_rev:
                logger.info("Database is already at the latest revision")
                self._log_migration_success(current_rev, target_rev)
                return True
            
            # Execute upgrade
            logger.info(f"Upgrading from {current_rev or 'base'} to {target_rev}")
            
            result = self._execute_migration_command("upgrade", target_rev)
            
            if result is None:
                logger.info("Dry run completed successfully")
            else:
                logger.info("Migration upgrade completed")
            
            # Verify success
            final_rev = self._get_current_revision()
            if final_rev != target_rev:
                logger.error(f"Migration verification failed. Expected: {target_rev}, Got: {final_rev}")
                return False
            
            # Log success
            self._log_migration_success(final_rev, target_rev)
            return True
            
        except Exception as e:
            self._log_migration_failure(e)
            raise
    
    def downgrade_to_base(self) -> bool:
        """Downgrade database to base (empty state)"""
        try:
            # Validate prerequisites
            if not self._validate_migration_prerequisites():
                logger.error("Migration prerequisites not met")
                return False
            
            # Get current revision
            current_rev = self._get_current_revision()
            target_rev = "base"
            
            # Log start
            self._log_migration_start(current_rev, target_rev)
            
            # Execute downgrade
            logger.info(f"Downgrading from {current_rev or 'base'} to {target_rev}")
            
            result = self._execute_migration_command("downgrade", target_rev)
            
            if result is None:
                logger.info("Dry run completed successfully")
            else:
                logger.info("Migration downgrade completed")
            
            # Verify success
            final_rev = self._get_current_revision()
            if final_rev != target_rev and final_rev is not None:
                logger.error(f"Migration verification failed. Expected: {target_rev}, Got: {final_rev}")
                return False
            
            # Log success
            self._log_migration_success(final_rev, target_rev)
            return True
            
        except Exception as e:
            self._log_migration_failure(e)
            raise
    
    def generate_revision(self, message: str, autogenerate: bool = True) -> bool:
        """Generate new migration revision"""
        try:
            logger.info(f"Generating new migration with message: {message}")
            
            if self.config.dry_run:
                logger.info("DRY RUN: Would generate new migration")
                return True
            
            # Generate revision
            result = self._execute_migration_command(
                "revision",
                "--autogenerate" if autogenerate else "",
                "-m", message
            )
            
            if result is None:
                logger.info("Dry run completed successfully")
            else:
                logger.info("Migration revision generated successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate revision: {str(e)}")
            raise
    
    def list_migrations(self) -> Dict[str, Any]:
        """List migration history"""
        try:
            # Get current revision
            current_rev = self._get_current_revision()
            
            # Get available migrations
            available_migrations = self._list_available_migrations()
            
            # Get migration history
            history = []
            try:
                result = self._execute_migration_command("history")
                if result:
                    history = [str(line) for line in result.split('\n') if line.strip()]
            except Exception as e:
                logger.warning(f"Could not get migration history: {str(e)}")
            
            return {
                "current_revision": current_rev,
                "available_migrations": available_migrations,
                "migration_history": history,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to list migrations: {str(e)}")
            raise
    
    def close(self) -> None:
        """Clean up resources"""
        try:
            self.connection_manager.close()
            logger.info("Migration executor cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
