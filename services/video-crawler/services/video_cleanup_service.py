"""Video cleanup operations extracted from main service."""

from typing import Any, Dict, Optional

from common_py.logging_config import configure_logging
from config_loader import config
from services.cleanup_service import cleanup_service

logger = configure_logging("video-crawler:cleanup_service")


class VideoCleanupService:
    """Handles video cleanup operations for the video crawler service."""

    def __init__(self, video_dir_override: Optional[str] = None):
        self._video_dir_override = video_dir_override

    async def run_auto_cleanup(self, job_id: str) -> None:
        """Run automatic video cleanup after processing.

        Args:
            job_id: Job identifier for logging
        """
        if not config.CLEANUP_OLD_VIDEOS:
            logger.debug("Auto cleanup disabled by configuration")
            return

        try:
            logger.info(f"[AUTO-CLEANUP] Starting cleanup for job {job_id}")

            video_dir = self._get_video_dir()
            cleanup_results = await cleanup_service.perform_cleanup(video_dir, dry_run=False)

            if cleanup_results['files_removed']:
                logger.info(
                    f"[AUTO-CLEANUP] Successfully cleaned up {len(cleanup_results['files_removed'])} "
                    f"files for job {job_id}"
                )
            else:
                logger.info(f"[AUTO-CLEANUP] No files to cleanup for job {job_id}")

        except Exception as e:
            logger.error(f"[AUTO-CLEANUP-ERROR] Failed to run cleanup for job {job_id}: {str(e)}")

    async def run_manual_cleanup(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run manual cleanup for debugging/testing purposes.

        Args:
            dry_run: If True, only list files without removing them

        Returns:
            Dictionary with cleanup results and information
        """
        try:
            logger.info(f"[MANUAL-CLEANUP] Starting cleanup (dry_run={dry_run})")

            base_dir = self._get_video_dir()
            cleanup_info = await cleanup_service.get_cleanup_info(base_dir)
            cleanup_results = await cleanup_service.perform_cleanup(base_dir, dry_run)

            return {
                'cleanup_info': cleanup_info,
                'cleanup_results': cleanup_results,
                'config': cleanup_service.get_status()
            }

        except Exception as e:
            logger.error(f"[MANUAL-CLEANUP-ERROR] Failed to run manual cleanup: {str(e)}")
            raise

    def _get_video_dir(self) -> str:
        """Get the video directory path."""
        return self._video_dir_override or config.VIDEO_DIR

    def get_cleanup_status(self) -> Dict[str, Any]:
        """Get current cleanup service status and configuration."""
        return {
            'enabled': config.CLEANUP_OLD_VIDEOS,
            'retention_days': config.VIDEO_RETENTION_DAYS,
            'video_dir': self._get_video_dir(),
            'service_status': cleanup_service.get_status()
        }