"""
Video cleanup service for automatically removing old video files.
"""

import asyncio
from typing import Dict, Any, List
from common_py.logging_config import configure_logging
from utils.file_cleanup import VideoCleanupManager
from config_loader import config

logger = configure_logging("video-crawler")


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
                f"[CLEANUP-COMPLETE] Cleanup completed: {len(cleanup_results['files_removed'])} files removed, {len(removed_dirs)} directories removed"
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


# Global cleanup service instance
cleanup_service = VideoCleanupService()
