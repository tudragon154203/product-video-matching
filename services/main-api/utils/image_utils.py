"""
Utility functions for image serving and URL derivation.
"""
import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from common_py.logging_config import configure_logging

logger = configure_logging("main-api:image_utils")


def to_public_url(local_path: Optional[str], data_root: str) -> Optional[str]:
    """
    Convert a local file path (relative to data_root) to a public URL for serving via /files endpoint.

    Args:
        local_path: Path to the file relative to the data_root (e.g., "images/123.jpg")
        data_root: The root data directory (e.g., "/app/data")

    Returns:
        Public URL relative to API root (e.g., "/files/images/123.jpg") or None if invalid
    """
    if not local_path or not isinstance(local_path, str) or not local_path.strip():
        logger.debug("Empty or invalid local_path provided")
        return None

    try:
        # Construct the full absolute path within the container
        full_path = Path(data_root) / local_path

        # Resolve the full path to handle any '..' or '.'
        resolved_full_path = full_path.resolve()
        resolved_data_root = Path(data_root).resolve()

        # Security check: ensure the resolved path is within the data root
        if not resolved_full_path.is_relative_to(resolved_data_root):
            logger.warning(
                f"Path {local_path} resolves outside data root {data_root}")
            return None

        # Ensure it's not a directory
        if resolved_full_path.is_dir():
            logger.debug(
                f"Path {resolved_full_path} is a directory, not a file")
            return None

        # Get the path relative to the data root for the URL
        relative_url_path = str(
            resolved_full_path.relative_to(resolved_data_root))

        # Normalize separators to forward slashes for URL
        relative_url_path = relative_url_path.replace(os.sep, '/')

        # Construct public URL as a relative path; FE prefixes with NEXT_PUBLIC_API_BASE_URL
        # Use quote for URL encoding
        public_url = f"/files/{quote(relative_url_path)}"
        return public_url

    except (ValueError, OSError) as e:
        logger.warning(
            f"Error converting path {local_path} to public URL: {e}")
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
