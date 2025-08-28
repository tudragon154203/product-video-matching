"""
Utility functions for image serving and URL derivation.
"""
import os
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

def to_public_url(local_path: Optional[str], data_root: str) -> Optional[str]:
    """
    Convert a local file path to a public URL for serving via /files endpoint.
    
    Args:
        local_path: Absolute path to the file inside the container (e.g., "/app/data/images/123.jpg")
        data_root: The root data directory (e.g., "/app/data")
    
    Returns:
        Public URL relative to /files (e.g., "/files/images/123.jpg") or None if invalid
    """
    if not local_path or not isinstance(local_path, str) or not local_path.strip():
        logger.debug("Empty or invalid local_path provided")
        return None
    
    try:
        # Security check: ensure path doesn't escape data root using abspath
        # This handles cases where path contains ../ by resolving them
        resolved_path = os.path.abspath(local_path)
        resolved_root = os.path.abspath(data_root)
        
        # Check if resolved path is within the resolved root
        if not resolved_path.startswith(resolved_root):
            logger.warning(f"Path {local_path} escapes data root {data_root}")
            return None
        
        # Check if it's a directory (path ends with separator or is a directory)
        if os.path.isdir(local_path):
            logger.debug(f"Path {local_path} is a directory, not a file")
            return None
        
        # Normalize paths to handle different separators
        local_path = os.path.normpath(local_path)
        data_root = os.path.normpath(data_root)
        
        # Get relative path from data_root
        relative_path = os.path.relpath(local_path, data_root)
        
        # Normalize separators to forward slashes for URL
        relative_path = relative_path.replace(os.sep, '/')
        
        # Construct public URL
        public_url = f"/files/{relative_path}"
        
        # Additional validation: ensure no path traversal in the final URL
        if ".." in public_url:
            logger.warning(f"Potential path traversal in URL: {public_url}")
            return None
        
        return public_url
        
    except (ValueError, OSError) as e:
        logger.warning(f"Error converting path {local_path} to public URL: {e}")
        return None

def get_mime_type(file_path: str) -> str:
    """
    Get MIME type for a file based on its extension.
    
    Args:
        file_path: Path to the file
    
    Returns:
        MIME type string
    """
    file_path = file_path.lower()
    
    # Common image MIME types
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml',
        '.bmp': 'image/bmp',
        '.tiff': 'image/tiff',
        '.ico': 'image/x-icon'
    }
    
    # Get file extension
    ext = Path(file_path).suffix
    return mime_types.get(ext, 'application/octet-stream')

def is_safe_path(file_path: str, base_path: str) -> bool:
    """
    Check if a file path is safe and doesn't escape the base directory.
    
    Args:
        file_path: Path to validate
        base_path: Base directory that should contain the file
    
    Returns:
        True if path is safe, False otherwise
    """
    try:
        # Resolve both paths to absolute paths
        file_path = os.path.abspath(file_path)
        base_path = os.path.abspath(base_path)
        
        # Check if file path starts with base path
        if not file_path.startswith(base_path):
            return False
        
        # Check for symlinks that might escape the base path
        if os.path.islink(file_path):
            real_path = os.path.realpath(file_path)
            if not real_path.startswith(base_path):
                return False
        
        return True
        
    except (OSError, ValueError):
        return False