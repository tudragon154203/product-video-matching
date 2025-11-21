"""Static file URL building service for main-api."""

import os
from pathlib import Path
from typing import Optional

from common_py.logging_config import configure_logging

logger = configure_logging("main-api:static_file_service")


class StaticFileService:
    """Service for building public URLs to static files."""

    def __init__(self, base_url: str, data_root: str):
        """
        Initialize static file service.

        Args:
            base_url: Base URL for the API (e.g., http://localhost:8000)
            data_root: Root directory for data files in container
        """
        self.base_url = base_url.rstrip('/')
        self.data_root = Path(data_root)

    def build_url_from_local_path(self, local_path: Optional[str]) -> Optional[str]:
        """
        Build a public URL from a local file path.

        Args:
            local_path: Local file path (e.g., /app/data/evidence/job123/img_frame.jpg)

        Returns:
            Public URL (e.g., http://localhost:8000/files/evidence/job123/img_frame.jpg)
            or None if path is invalid
        """
        if not local_path:
            return None

        try:
            path = Path(local_path)

            # Check if file exists
            if not path.exists():
                logger.warning(
                    "File does not exist",
                    local_path=local_path,
                )
                return None

            # Get relative path from data root
            try:
                relative_path = path.relative_to(self.data_root)
            except ValueError:
                logger.warning(
                    "Path is not relative to data root",
                    local_path=local_path,
                    data_root=str(self.data_root),
                )
                return None

            # Build URL
            url = f"{self.base_url}/files/{relative_path.as_posix()}"
            return url

        except Exception as e:
            logger.error(
                "Failed to build URL from local path",
                local_path=local_path,
                error=str(e),
            )
            return None
