#!/usr/bin/env python3
"""
Robust database migration runner using Alembic.
Implements retry logic, error handling, and comprehensive logging.
"""
import argparse
import sys
import os
import traceback
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common_py.migration_service import (
    MigrationService,
    MigrationAction,
    MigrationError,
    create_migration_service
)
from common_py.logging_config import configure_logging

logger = configure_logging("scripts:run_migrations")


def setup_argument_parser() -> argparse.ArgumentParser:
    """Setup command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Run database migrations with robust error handling and retry logic"
    )
    
    parser.add_argument(
        "action",
        choices=["upgrade", "downgrade", "status", "list", "validate", "generate"],
        help="Migration action to perform"
    )
    
    parser.add_argument(
        "--message",
        help="Message for new migration (required for generate action)"
    )
    
    parser.add_argument(
        "--autogenerate",
        action="store_true",
        default=True,
        help="Autogenerate migration (default: True)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform dry run without actual changes"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--service-name",
        default="migration_runner",
        help="Service name for logging (default: migration_runner)"
    )
    
    parser.add_argument(
        "--config",
        help="Path to migration configuration file"
    )
    
    return parser


def handle_migration_result(result: dict, action: str) -> int:
    """Handle migration result and return exit code"""
    if result.get("success", False):
        logger.info(f"Migration '{action}' completed successfully")
        if "duration_seconds" in result:
            logger.info(f"Duration: {result['duration_seconds']:.2f} seconds")
        return 0
    else:
        logger.error(f"Migration '{action}' failed")
        return 1


def main() -> int:
    """Main migration runner function"""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    try:
        # Setup logging
        log_level = "DEBUG" if args.verbose else "INFO"
        configure_logging("scripts:run_migrations", log_level)
        
        logger.info(f"Starting migration runner for action: {args.action}")
        
        # Create migration service
        service = MigrationService(args.service_name)
        
        # Override environment variables if provided
        if args.dry_run:
            os.environ["MIGRATION_DRY_RUN"] = "true"
        if args.verbose:
            os.environ["MIGRATION_VERBOSE"] = "true"
        
        # Initialize service
        service.initialize()
        
        # Handle different actions
        if args.action == "upgrade":
            result = service.run_migration(MigrationAction.UPGRADE)
            
        elif args.action == "downgrade":
            result = service.run_migration(MigrationAction.DOWNGRADE)
            
        elif args.action == "status":
            result = service.get_migration_status()
            print("\n=== Migration Status ===")
            for key, value in result.items():
                print(f"{key}: {value}")
            print("========================\n")
            return 0
            
        elif args.action == "list":
            result = service.list_migrations()
            print("\n=== Migration List ===")
            if "available_migrations" in result:
                print("Available migrations:")
                for migration in result["available_migrations"]:
                    print(f"  - {migration}")
            if "current_revision" in result:
                print(f"Current revision: {result['current_revision']}")
            print("=====================\n")
            return 0
            
        elif args.action == "validate":
            result = service.validate_environment()
            print("\n=== Environment Validation ===")
            for key, value in result.items():
                print(f"{key}: {value}")
            print("=============================\n")
            return 0 if result.get("prerequisites_met", False) else 1
            
        elif args.action == "generate":
            if not args.message:
                logger.error("Message is required for generate action")
                return 1
            result = service.generate_migration(args.message, args.autogenerate)
            
        else:
            logger.error(f"Unknown action: {args.action}")
            return 1
        
        # Handle result
        return handle_migration_result(result, args.action)
        
    except MigrationError as e:
        logger.error(f"Migration error: {str(e)}")
        return 1
        
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        return 130
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.debug(traceback.format_exc())
        return 1
        
    finally:
        # Cleanup
        if 'service' in locals():
            service.cleanup()


if __name__ == "__main__":
    sys.exit(main())
