"""
File cleanup utilities for video crawler service.

Provides functionality to automatically remove old video files based on age.
"""

import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler")


class VideoCleanupManager:
    """Handles automatic cleanup of old video files."""
    
    def __init__(self, days_to_keep: int = 7):
        """
        Initialize the cleanup manager.
        
        Args:
            days_to_keep: Number of days to keep video files (default: 7)
        """
        self.retention_days = days_to_keep
        self.cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
    def should_cleanup_file(self, file_path: str) -> bool:
        """
        Check if a file should be cleaned up based on age
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file should be cleaned up, False otherwise
        """
        try:
            file_stat = os.stat(file_path)
            file_mod_time = datetime.fromtimestamp(file_stat.st_mtime)
            
            return file_mod_time < self.cutoff_date
            
        except FileNotFoundError:
            logger.warning(f"File not found during cleanup check: {file_path}")
            return False
        except Exception as e:
            logger.error(f"Error checking file age for {file_path}: {str(e)}")
            return False
    
    def find_old_files(self, video_dir: str) -> List[Dict[str, Any]]:
        """
        Find all video files older than the retention period.
        
        Args:
            video_dir: Directory to search for video files
            
        Returns:
            List of dictionaries with file information
        """
        old_files = []
        
        if not os.path.exists(video_dir):
            logger.warning(f"Video directory does not exist: {video_dir}")
            return old_files
            
        # Walk through all uploader directories
        for uploader_dir in Path(video_dir).iterdir():
            if not uploader_dir.is_dir():
                continue
                
            for file_path in uploader_dir.rglob("*"):
                if file_path.is_file():
                    file_info = self._get_file_info(file_path, uploader_dir.name)
                    if file_info and file_info['is_old']:
                        old_files.append(file_info)
                        
        logger.info(f"Found {len(old_files)} video files older than {self.retention_days} days")
        return old_files
    
    def _get_file_info(self, file_path: Path, uploader_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a file and check if it's old.
        
        Args:
            file_path: Path to the file
            uploader_name: Name of the uploader directory
            
        Returns:
            Dictionary with file info or None if file cannot be processed
        """
        try:
            # Get file stats
            stat = file_path.stat()
            create_time = datetime.fromtimestamp(stat.st_mtime)
            file_size = stat.st_size
            
            # Check if file is older than cutoff
            is_old = create_time < self.cutoff_date
            
            return {
                'path': str(file_path.absolute()),
                'filename': file_path.name,
                'uploader': uploader_name,
                'create_time': create_time,
                'file_size': file_size,
                'is_old': is_old,
                'file_age_days': (datetime.now() - create_time).days
            }
            
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {str(e)}")
            return None
    
    def cleanup_old_files(self, video_dir: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Remove all video files older than the retention period.
        
        Args:
            video_dir: Directory to clean up
            dry_run: If True, only list files that would be removed
            
        Returns:
            Dictionary with cleanup results
        """
        old_files = self.find_old_files(video_dir)
        results = {
            'files_removed': [],
            'files_skipped': [],
            'total_size_freed': 0,
            'total_files': len(old_files),
            'dry_run': dry_run
        }
        
        if not old_files:
            logger.info("No old files to clean up")
            return results
            
        for file_info in old_files:
            try:
                if dry_run:
                    results['files_skipped'].append(file_info)
                else:
                    file_size = file_info['file_size']
                    os.remove(file_info['path'])
                    results['files_removed'].append(file_info)
                    results['total_size_freed'] += file_size
                    logger.info(f"[CLEANUP-REMOVED] {file_info['filename']} | Size: {file_size/1024/1024:.2f}MB | Age: {file_info['file_age_days']} days | Uploader: {file_info['uploader']}")
                        
            except Exception as e:
                logger.error(f"[CLEANUP-ERROR] Failed to remove {file_info['filename']}: {str(e)}")
                results['files_skipped'].append(file_info)
        
        # Log summary
        if results['files_removed']:
            freed_mb = results['total_size_freed'] / (1024 * 1024)
            logger.info(f"[CLEANUP-SUMMARY] Removed {len(results['files_removed'])} files, freed {freed_mb:.2f}MB (dry_run={dry_run})")
            
        if results['files_skipped']:
            logger.warning(f"[CLEANUP-SKIPPED] {len(results['files_skipped'])} files could not be removed")
            
        return results
    
    def cleanup_empty_directories(self, video_dir: str, dry_run: bool = False) -> List[str]:
        """
        Remove empty uploader directories.
        
        Args:
            video_dir: Base video directory
            dry_run: If True, only list directories that would be removed
            
        Returns:
            List of directories that were/would be removed
        """
        removed_dirs = []
        
        for uploader_dir in Path(video_dir).iterdir():
            if uploader_dir.is_dir():
                try:
                    # Check if directory is empty
                    if any(uploader_dir.iterdir()):
                        continue
                        
                    if dry_run:
                        removed_dirs.append(str(uploader_dir))
                        logger.info(f"[DIR-REMOVAL-DRY-RUN] Would remove empty directory: {uploader_dir}")
                    else:
                        uploader_dir.rmdir()
                        removed_dirs.append(str(uploader_dir))
                        logger.info(f"[DIR-REMOVED] Removed empty directory: {uploader_dir}")
                        
                except Exception as e:
                    logger.error(f"[DIR-ERROR] Could not process directory {uploader_dir}: {str(e)}")
                    
        return removed_dirs


def find_old_videos(video_dir: str, days_to_keep: int = 7) -> List[Dict[str, Any]]:
    """
    Convenience function to find old video files.
    
    Args:
        video_dir: Directory to search
        days_to_keep: Number of days to keep
        
    Returns:
        List of old file information
    """
    cleanup_manager = VideoCleanupManager(days_to_keep)
    return cleanup_manager.find_old_files(video_dir)


def cleanup_old_videos(video_dir: str, days_to_keep: int = 7, dry_run: bool = False) -> Dict[str, Any]:
    """
    Convenience function to clean up old video files.
    
    Args:
        video_dir: Directory to clean up
        days_to_keep: Number of days to keep
        dry_run: If True, only list files that would be removed
        
    Returns:
        Dictionary with cleanup results
    """
    cleanup_manager = VideoCleanupManager(days_to_keep)
    return cleanup_manager.cleanup_old_files(video_dir, dry_run)