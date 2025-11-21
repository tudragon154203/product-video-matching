"""Static file URL building service for main-api."""

import os
import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Request
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
        self.data_root = Path(data_root).resolve()

    def get_secure_file_path(self, filename: str) -> Path:
        """
        Get secure file path, preventing path traversal attacks.

        Args:
            filename: Requested filename (relative path)

        Returns:
            Resolved Path object

        Raises:
            ValueError: If path traversal detected
        """
        # Construct full path
        requested_path = (self.data_root / filename).resolve()

        # Ensure the resolved path is within data_root
        if not str(requested_path).startswith(str(self.data_root)):
            raise ValueError(f"Path traversal detected: {filename}")

        # Check for symlink path traversal
        if requested_path.is_symlink():
            real_path = requested_path.resolve()
            if not str(real_path).startswith(str(self.data_root)):
                raise ValueError(f"Symlink path traversal detected: {filename}")

        return requested_path

    def validate_file_access(self, file_path: Path) -> None:
        """
        Validate that file exists and is accessible.

        Args:
            file_path: Path to validate

        Raises:
            HTTPException: If file not found or not accessible
        """
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if not file_path.is_file():
            raise HTTPException(status_code=403, detail="Not a file")

        if not os.access(file_path, os.R_OK):
            raise HTTPException(status_code=403, detail="File not readable")

    def get_content_type(self, file_path: Path) -> str:
        """
        Determine MIME type for file.

        Args:
            file_path: Path to file

        Returns:
            MIME type string
        """
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or "application/octet-stream"

    def log_request(
        self,
        request: Request,
        filename: str,
        file_path: Optional[Path],
        status: int = 200
    ) -> None:
        """
        Log file access request.

        Args:
            request: FastAPI request object
            filename: Requested filename
            file_path: Resolved file path (if available)
            status: HTTP status code
        """
        logger.info(
            "Static file request",
            filename=filename,
            file_path=str(file_path) if file_path else None,
            status=status,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

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
