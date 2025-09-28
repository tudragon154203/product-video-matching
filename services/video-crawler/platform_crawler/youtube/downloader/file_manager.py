import os
import time
from pathlib import Path

from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler:file_manager")

class FileManager:
    """Handles file operations for YouTube video downloads"""
    
    @staticmethod
    def create_uploader_directory(download_dir: str, uploader: str) -> Path:
        """
        Create directory for uploader
        
        Args:
            download_dir: Base download directory
            uploader: Uploader name
            
        Returns:
            Path: Path to the uploader directory
        """
        uploader_dir = Path(download_dir) / uploader
        uploader_dir.mkdir(parents=True, exist_ok=True)
        return uploader_dir
    
    @staticmethod
    def check_existing_file(uploader_dir: Path, title: str) -> str:
        """
        Check if file already exists
        
        Args:
            uploader_dir: Directory for the uploader
            title: Video title
            
        Returns:
            str: Path to existing file or None if not found
        """
        existing_files = list(uploader_dir.glob(f"{title}.*"))
        if existing_files:
            return str(existing_files[0].absolute())
        return None
    
    @staticmethod
    def find_downloaded_file(uploader_dir: Path, title: str) -> str:
        """
        Find the downloaded file
        
        Args:
            uploader_dir: Directory for the uploader
            title: Video title
            
        Returns:
            str: Path to downloaded file or None if not found
        """
        downloaded_files = list(uploader_dir.glob(f"{title}.*"))
        if downloaded_files:
            return str(downloaded_files[0].absolute())
        return None
    
    @staticmethod
    def validate_downloaded_file(file_path: str) -> bool:
        """
        Validate that downloaded file is not empty
        
        Args:
            file_path: Path to the downloaded file
            
        Returns:
            bool: True if file is valid, False otherwise
        """
        if not file_path or not os.path.exists(file_path):
            return False
            
        file_size = os.path.getsize(file_path)
        return file_size > 0
    
    @staticmethod
    def remove_file(file_path: str) -> bool:
        """
        Remove a file
        
        Args:
            file_path: Path to the file to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception as e:
            logger.error(f"[FILE-REMOVE-ERROR] Could not remove file {file_path}: {str(e)}")
        return False
    
    @staticmethod
    def log_download_success(title: str, file_path: str, start_time: float) -> None:
        """
        Log successful download
        
        Args:
            title: Video title
            file_path: Path to downloaded file
            start_time: Start time of download
        """
        duration = time.time() - start_time
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
        logger.info(f"[DOWNLOAD-SUCCESS] Video: {title} | Duration: {duration:.2f}s | Size: {file_size:.2f}MB | Path: {file_path}")
