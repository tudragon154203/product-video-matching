"""
Utility functions for image serving and URL derivation.
"""
import os
import ntpath
import re
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from common_py.logging_config import configure_logging

logger = configure_logging("main-api:image_utils")
WINDOWS_ROOT_PATTERN = re.compile(r'^(?:[a-zA-Z]:[\\/]|\\\\)')


def _looks_like_windows_root(path: str) -> bool:
    """Check whether a path string appears to describe a Windows absolute path."""
    if not path:
        return False
    return bool(WINDOWS_ROOT_PATTERN.match(path))


def _to_public_url_windows(local_path: str, data_root: str) -> Optional[str]:
    """Windows-aware implementation of the local-path to public URL conversion."""
    normalized_root = ntpath.normpath(data_root)
    normalized_local = ntpath.normpath(local_path)

    if not normalized_root:
        logger.debug("Empty normalized Windows data_root provided")
        return None

    if ntpath.isabs(normalized_local):
        full_path = normalized_local
    else:
        full_path = ntpath.normpath(ntpath.join(normalized_root, normalized_local))

    if os.path.isdir(full_path):
        logger.debug(
            f"Windows path {local_path} refers to a directory")
        return None

    try:
        common_root = ntpath.commonpath([ntpath.normcase(normalized_root), ntpath.normcase(full_path)])
    except ValueError:
        logger.warning(
            f"Windows path {local_path} is not within data root {data_root}")
        return None

    if common_root != ntpath.normcase(normalized_root):
        logger.warning(
            f"Windows path {local_path} resolves outside data root {data_root}")
        return None

    try:
        relative = ntpath.relpath(full_path, normalized_root)
    except ValueError as exc:
        logger.warning(
            f"Unable to derive relative Windows path for {local_path}: {exc}")
        return None

    if relative in ('.', '') or relative.startswith('..'):
        logger.debug(
            f"Windows path {local_path} is not a valid file under data root {data_root}")
        return None

    relative_url_path = relative.replace('\\', '/')
    return f"/files/{quote(relative_url_path)}"


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

    if not data_root or not isinstance(data_root, str) or not data_root.strip():
        logger.debug("Empty or invalid data_root provided")
        return None

    cleaned_local_path = local_path.strip()
    cleaned_data_root = data_root.strip()

    if _looks_like_windows_root(cleaned_data_root) or _looks_like_windows_root(cleaned_local_path):
        return _to_public_url_windows(cleaned_local_path, cleaned_data_root)

    try:
        full_path = Path(cleaned_data_root) / cleaned_local_path
        resolved_full_path = full_path.resolve()
        resolved_data_root = Path(cleaned_data_root).resolve()

        if not resolved_full_path.is_relative_to(resolved_data_root):
            logger.warning(
                f"Path {cleaned_local_path} resolves outside data root {cleaned_data_root}")
            return None

        if resolved_full_path.is_dir():
            logger.debug(
                f"Path {resolved_full_path} is a directory, not a file")
            return None

        relative_url_path = str(resolved_full_path.relative_to(resolved_data_root))
        relative_url_path = relative_url_path.replace(os.sep, '/').replace('\\', '/')
        public_url = f"/files/{quote(relative_url_path)}"
        return public_url

    except (ValueError, OSError) as e:
        logger.warning(
            f"Error converting path {cleaned_local_path} to public URL: {e}")
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
