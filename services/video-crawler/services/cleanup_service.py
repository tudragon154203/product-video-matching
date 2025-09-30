"""
Video cleanup service for automatically removing old video files.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from common_py.logging_config import configure_logging
from config_loader import config
from utils.file_cleanup import VideoCleanupManager

logger = configure_logging("video-crawler:cleanup_service")


class VideoCleanupService:
    """Service for managing automatic video cleanup."""

    def __init__(self):
        self.cleanup_manager = VideoCleanupManager(config.VIDEO_RETENTION_DAYS)
        self.enabled = config.CLEANUP_OLD_VIDEOS

    async def perform_cleanup(self, video_dir: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Perform automatic cleanup of old video files.

        Args:
            video_dir: Directory containing video files
            dry_run: If True, only list files without removing them

        Returns:
            Dictionary with cleanup results
        """
        if not self.enabled:
            logger.info("[CLEANUP-SKIPPED] Auto cleanup is disabled")
            return {
                'files_removed': [],
                'files_skipped': [],
                'total_size_freed': 0,
                'total_files': 0,
                'dry_run': dry_run,
                'enabled': False
            }

        try:
            logger.info(f"[CLEANUP-START] Starting cleanup of videos older than {config.VIDEO_RETENTION_DAYS} days (dry_run={dry_run})")

            # Validate directory exists
            from pathlib import Path
            if not Path(video_dir).exists():
                logger.warning(f"Video directory does not exist: {video_dir}")
                return {
                    'files_removed': [],
                    'files_skipped': [],
                    'total_size_freed': 0,
                    'total_files': 0,
                    'dry_run': dry_run,
                    'enabled': False,
                    'empty_dirs_removed': [],
                    'total_dirs_removed': 0,
                }

            # Clean up old files
            cleanup_results = self.cleanup_manager.cleanup_old_files(video_dir, dry_run)

            # Clean up empty directories
            removed_dirs = self.cleanup_manager.cleanup_empty_directories(video_dir, dry_run)

            # Combine results
            final_results = {
                **cleanup_results,
                'empty_dirs_removed': removed_dirs,
                'total_dirs_removed': len(removed_dirs),
                'enabled': True
            }

            logger.info(
                f"[CLEANUP-COMPLETE] Cleanup completed: {len(cleanup_results['files_removed'])} files removed, "
                f"{len(removed_dirs)} directories removed"
            )
            return final_results

        except Exception as e:
            logger.error(f"[CLEANUP-ERROR] Failed to perform cleanup: {str(e)}")
            # Handle errors gracefully and return a safe response
            return {
                'files_removed': [],
                'files_skipped': [],
                'total_size_freed': 0,
                'total_files': 0,
                'dry_run': dry_run,
                'enabled': False,
                'empty_dirs_removed': [],
                'total_dirs_removed': 0,
                'error': str(e),
            }

    async def get_cleanup_info(self, video_dir: str) -> Dict[str, Any]:
        """
        Get information about what would be cleaned up.

        Args:
            video_dir: Directory to check

        Returns:
            Dictionary with cleanup information
        """
        try:
            old_files = self.cleanup_manager.find_old_files(video_dir)
            total_size = sum(f['file_size'] for f in old_files)

            return {
                'total_old_files': len(old_files),
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'retention_days': config.VIDEO_RETENTION_DAYS,
                'cleanup_enabled': self.enabled,
                # Oldest = largest age (max), Newest = smallest age (min)
                'oldest_file': max(old_files, key=lambda x: x['file_age_days']) if old_files else None,
                'newest_file': min(old_files, key=lambda x: x['file_age_days']) if old_files else None
            }

        except Exception as e:
            logger.error(f"[CLEANUP-INFO-ERROR] Failed to get cleanup info: {str(e)}")
            raise

    async def enable_cleanup(self, enabled: bool = True) -> None:
        """
        Enable or disable automatic cleanup.

        Args:
            enabled: Whether cleanup should be enabled
        """
        self.enabled = enabled
        logger.info(f"[CLEANUP-CONFIG] Auto cleanup {'enabled' if enabled else 'disabled'}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current cleanup service status.

        Returns:
            Dictionary with service status
        """
        return {
            'enabled': self.enabled,
            'retention_days': config.VIDEO_RETENTION_DAYS,
            'video_dir': config.VIDEO_DIR
        }

    async def cleanup_tiktok_videos(self, days: int = 7) -> Dict[str, Any]:
        """
        Clean up TikTok videos older than specified number of days.

        Args:
            days: Number of days to keep videos (default: 7)

        Returns:
            Dictionary with cleanup results
        """
        try:
            tiktok_video_path = config.TIKTOK_VIDEO_STORAGE_PATH

            logger.info(f"[TIKTOK-CLEANUP] Starting cleanup of TikTok videos older than {days} days from {tiktok_video_path}")

            # Validate directory exists
            if not Path(tiktok_video_path).exists():
                logger.warning(f"[TIKTOK-CLEANUP] TikTok video directory does not exist: {tiktok_video_path}")
                return {
                    'videos_removed': [],
                    'videos_skipped': [],
                    'total_size_freed': 0,
                    'total_videos': 0,
                    'days_threshold': days,
                    'path': tiktok_video_path,
                    'error': 'Directory does not exist'
                }

            cutoff_date = datetime.now() - timedelta(days=days)
            videos_removed = []
            videos_skipped = []
            total_size_freed = 0

            # Scan for TikTok video files
            for file_path in Path(tiktok_video_path).glob("*.mp4"):
                try:
                    # Check file modification time
                    file_mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)

                    if file_mod_time < cutoff_date:
                        # Remove old video file
                        file_size = file_path.stat().st_size
                        file_path.unlink()

                        videos_removed.append({
                            'filename': file_path.name,
                            'path': str(file_path),
                            'size_bytes': file_size,
                            'modified_time': file_mod_time.isoformat(),
                            'days_old': (datetime.now() - file_mod_time).days
                        })

                        total_size_freed += file_size
                        logger.info(
                            f"[TIKTOK-CLEANUP] Removed old video: {file_path.name} "
                            f"({file_size} bytes, {(datetime.now() - file_mod_time).days} days old)")
                    else:
                        videos_skipped.append({
                            'filename': file_path.name,
                            'path': str(file_path),
                            'modified_time': file_mod_time.isoformat(),
                            'days_old': (datetime.now() - file_mod_time).days
                        })

                except Exception as e:
                    logger.error(f"[TIKTOK-CLEANUP] Error processing file {file_path}: {str(e)}")
                    videos_skipped.append({
                        'filename': file_path.name,
                        'path': str(file_path),
                        'error': str(e)
                    })

            logger.info(f"[TIKTOK-CLEANUP] Cleanup completed: {len(videos_removed)} videos removed, {len(videos_skipped)} videos kept")

            return {
                'videos_removed': videos_removed,
                'videos_skipped': videos_skipped,
                'total_size_freed': total_size_freed,
                'total_videos': len(videos_removed) + len(videos_skipped),
                'days_threshold': days,
                'path': tiktok_video_path,
                'size_freed_mb': total_size_freed / (1024 * 1024)
            }

        except Exception as e:
            logger.error(f"[TIKTOK-CLEANUP-ERROR] Failed to cleanup TikTok videos: {str(e)}")
            return {
                'videos_removed': [],
                'videos_skipped': [],
                'total_size_freed': 0,
                'total_videos': 0,
                'days_threshold': days,
                'path': config.TIKTOK_VIDEO_STORAGE_PATH,
                'error': str(e)
            }


# Global cleanup service instance
cleanup_service = VideoCleanupService()
