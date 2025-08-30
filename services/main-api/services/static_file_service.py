"""
Service for handling static file operations and security checks.
"""
import os
import logging
from pathlib import Path
from typing import Optional

from config_loader import config
from utils.image_utils import get_mime_type

logger = logging.getLogger(__name__)


class StaticFileService:
    """Service for handling static file operations and security checks."""
    
    def __init__(self):
        self.data_root = Path(config.DATA_ROOT_CONTAINER).resolve()
        os.makedirs(self.data_root, exist_ok=True)
    
    def build_full_url(self, relative_path: str) -> str:
        """Build full URL for a relative path."""
        # Normalize path separators
        normalized_path = relative_path.replace(os.sep, '/')
        # Avoid double slashes
        if normalized_path.startswith('/'):
            normalized_path = normalized_path[1:]
        return f"{self.data_root}/files/{normalized_path}"
    
    def get_relative_path(self, local_path: str) -> str:
        """Get relative path from local path for URL building."""
        # Use pathlib for robust path manipulation
        local_path_obj = Path(local_path).resolve()
        
        # Ensure the local path is within the data root
        if not local_path_obj.is_relative_to(self.data_root):
            logger.warning(f"Path {local_path} is outside data root {self.data_root}")
            raise ValueError(f"Path {local_path} is outside data root")
        
        return str(local_path_obj.relative_to(self.data_root))
    
    def build_url_from_local_path(self, local_path: Optional[str]) -> Optional[str]:
        """Build full URL from local path."""
        if not local_path:
            return None
        
        try:
            relative_path = self.get_relative_path(local_path)
            return self.build_full_url(relative_path)
        except ValueError:
            logger.warning(f"Cannot build URL for local path: {local_path}")
            return None
    
    def get_secure_file_path(self, filename: str) -> Path:
        """Get secure file path with validation."""
        try:
            # Join requested file path with data root
            file_path = (self.data_root / filename).resolve()
            
            # Security check: ensure file is within data root
            if not file_path.is_relative_to(self.data_root):
                logger.warning(f"Path traversal attempt: {filename}")
                raise ValueError(f"Path traversal attempt: {filename}")
            
            return file_path
            
        except (ValueError, RuntimeError) as e:
            logger.warning(f"Path resolution failed for {filename}: {e}")
            raise e
    
    def validate_file_access(self, file_path: Path) -> None:
        """Validate file access permissions and existence."""
        if not file_path.exists():
            logger.info(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if file_path.is_dir():
            logger.warning(f"Directory access attempt: {file_path}")
            raise IsADirectoryError(f"Directory access attempt: {file_path}")
        
        if not os.access(file_path, os.R_OK):
            logger.warning(f"No read permission for: {file_path}")
            raise PermissionError(f"No read permission for: {file_path}")
    
    def get_content_type(self, file_path: Path) -> str:
        """Get MIME type for file."""
        return get_mime_type(str(file_path))
    
    def get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes."""
        if not file_path.exists():
            return 0
        return file_path.stat().st_size