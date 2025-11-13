"""
Test Media Manager
Auto-copies test media files from mock_data to data/ directory before tests run.
This ensures test media files are always available even if data/ is cleaned up.
"""

import shutil
from pathlib import Path
from typing import Optional
from common_py.logging_config import configure_logging

logger = configure_logging("test-utils:media-manager")


class TestMediaManager:
    """Manages test media files by auto-copying from mock_data to data/ directory."""

    def __init__(self, workspace_root: Optional[Path] = None):
        if workspace_root is None:
            # Auto-detect workspace root
            current_file = Path(__file__).resolve()
            workspace_root = current_file.parent.parent.parent

        self.workspace_root = workspace_root
        self.mock_data_dir = self.workspace_root / "tests" / "mock_data"
        self.data_tests_dir = self.workspace_root / "data" / "tests"

    def ensure_test_media_available(self) -> bool:
        """
        Ensure test media files are available by copying from mock_data if needed.

        Returns:
            bool: True if media files are available, False otherwise
        """
        try:
            # Check if mock_data exists
            if not self.mock_data_dir.exists():
                logger.warning(f"Mock data directory not found: {self.mock_data_dir}")
                return False

            # Define media directories to copy
            media_dirs = [
                ("products/ready", "Product test images"),
                ("videos/ready", "Video test frames")
            ]

            success = True
            for relative_dir, description in media_dirs:
                source_dir = self.mock_data_dir / relative_dir
                target_dir = self.data_tests_dir / relative_dir

                if not source_dir.exists():
                    logger.warning(f"Source media directory not found: {source_dir}")
                    success = False
                    continue

                # Create target directory if it doesn't exist
                target_dir.mkdir(parents=True, exist_ok=True)

                # Copy files if target is empty or has fewer files
                source_files = list(source_dir.glob("*"))
                target_files = list(target_dir.glob("*"))

                if len(target_files) < len(source_files):
                    logger.info(f"Copying {description} from {source_dir} to {target_dir}")

                    for source_file in source_files:
                        if source_file.is_file():
                            target_file = target_dir / source_file.name
                            shutil.copy2(source_file, target_file)
                            logger.debug(f"Copied: {source_file.name}")

                    logger.info(f"Copied {len(source_files)} {description}")
                else:
                    logger.debug(f"{description} already available ({len(target_files)} files)")

            return success

        except Exception as e:
            logger.error(f"Failed to ensure test media availability: {e}")
            return False

    def backup_current_media(self) -> bool:
        """
        Backup current test media to mock_data.
        This should be called when new media files are added.

        Returns:
            bool: True if backup successful, False otherwise
        """
        try:
            # Create mock_data directory structure
            self.mock_data_dir.mkdir(parents=True, exist_ok=True)

            # Define media directories to backup
            media_dirs = [
                ("products/ready", "Product test images"),
                ("videos/ready", "Video test frames")
            ]

            success = True
            for relative_dir, description in media_dirs:
                source_dir = self.data_tests_dir / relative_dir
                target_dir = self.mock_data_dir / relative_dir

                if not source_dir.exists():
                    logger.debug(f"Source directory not found for backup: {source_dir}")
                    continue

                # Create target directory
                target_dir.mkdir(parents=True, exist_ok=True)

                # Copy files
                source_files = [f for f in source_dir.glob("*") if f.is_file()]
                for source_file in source_files:
                    target_file = target_dir / source_file.name
                    shutil.copy2(source_file, target_file)

                logger.info(f"Backed up {len(source_files)} {description}")

            return success

        except Exception as e:
            logger.error(f"Failed to backup test media: {e}")
            return False

    def verify_media_integrity(self) -> bool:
        """
        Verify that test media files exist and are not corrupted.

        Returns:
            bool: True if all media files are available and valid
        """
        try:
            media_files = []

            # Check product images
            products_dir = self.data_tests_dir / "products" / "ready"
            if products_dir.exists():
                media_files.extend(products_dir.glob("*.jpg"))
                media_files.extend(products_dir.glob("*.png"))

            # Check video frames
            videos_dir = self.data_tests_dir / "videos" / "ready"
            if videos_dir.exists():
                media_files.extend(videos_dir.glob("*.jpg"))
                media_files.extend(videos_dir.glob("*.png"))

            if not media_files:
                logger.warning("No test media files found")
                return False

            # Check file sizes (basic integrity check)
            for media_file in media_files:
                if media_file.stat().st_size == 0:
                    logger.error(f"Empty media file: {media_file}")
                    return False

            logger.info(f"Verified {len(media_files)} test media files")
            return True

        except Exception as e:
            logger.error(f"Failed to verify media integrity: {e}")
            return False


# Global instance for easy access
_media_manager = None


def get_media_manager(workspace_root: Optional[Path] = None) -> TestMediaManager:
    """Get or create the global media manager instance."""
    global _media_manager
    if _media_manager is None:
        _media_manager = TestMediaManager(workspace_root)
    return _media_manager


def ensure_test_media_available(workspace_root: Optional[Path] = None) -> bool:
    """
    Convenience function to ensure test media files are available.
    This can be called from test setup.

    Args:
        workspace_root: Path to workspace root (auto-detected if None)

    Returns:
        bool: True if media files are available
    """
    manager = get_media_manager(workspace_root)
    return manager.ensure_test_media_available()


def backup_test_media(workspace_root: Optional[Path] = None) -> bool:
    """
    Convenience function to backup current test media to mock_data.

    Args:
        workspace_root: Path to workspace root (auto-detected if None)

    Returns:
        bool: True if backup successful
    """
    manager = get_media_manager(workspace_root)
    return manager.backup_current_media()
