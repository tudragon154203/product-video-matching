"""
Static file serving endpoints for images and other media files.
"""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Depends, Response
from fastapi.responses import FileResponse
from starlette.responses import RedirectResponse
from typing import Optional

from config_loader import config
from utils.image_utils import get_mime_type, is_safe_path
from api.dependency import get_db
from services.static_file_service import StaticFileService
from common_py.logging_config import configure_logging

logger = configure_logging("main-api:static_endpoints")

router = APIRouter()

# Dependency function


def get_static_file_service() -> StaticFileService:
    return StaticFileService()


@router.get("/files/{filename:path}")
async def serve_static_file(
    filename: str,
    request: Request,
    response: Response,
    static_service: StaticFileService = Depends(get_static_file_service)
):
    """
    Serve static files directly through API routes.

    Args:
        filename: The requested file path (relative to DATA_ROOT)
        request: The incoming HTTP request
        response: The outgoing HTTP response

    Returns:
        FileResponse: The requested file
    """
    try:
        # Use service for secure file path handling
        file_path = static_service.get_secure_file_path(filename)

        # Validate file access
        static_service.validate_file_access(file_path)

        # Determine the content type so it can be applied to the response
        mime_type = static_service.get_content_type(file_path)

        # Log the request for observability
        static_service.log_request(request, filename, file_path)

        # Serve the file with appropriate headers
        file_response = FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type=mime_type
        )
        file_response.headers["cache-control"] = "public, max-age=3600"
        return file_response
    except HTTPException:
        # Log error cases
        # Note: file_path might not be defined if an exception occurred early
        try:
            static_service.log_request(request, filename, file_path, status=404 if "not found" in str(
                locals().get('file_path', '')) else 403)
        except:
            pass  # Ignore logging errors
        raise
    except FileNotFoundError:
        # Handle file not found specifically
        try:
            static_service.log_request(
                request, filename, file_path, status=404)
        except:
            pass  # Ignore logging errors
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Error serving file {filename}: {e}")
        # Note: file_path might not be defined if an exception occurred early
        try:
            static_service.log_request(
                request, filename, file_path, status=500)
        except:
            pass  # Ignore logging errors
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def static_files_health(static_service: StaticFileService = Depends(get_static_file_service)):
    """
    Health check for static files service.

    Returns:
        dict: Health status information
    """
    try:
        # Check if data directory exists and is readable
        if not os.path.exists(static_service.data_root):
            return {"status": "error", "message": "Data directory not found"}

        # Try to list files to verify permissions
        try:
            files = os.listdir(static_service.data_root)
            return {
                "status": "healthy",
                "message": "Static files service is operational",
                "data_directory": str(static_service.data_root),
                "file_count": len(files),
                "sample_files": files[:5]  # Show first 5 files for debugging
            }
        except PermissionError:
            return {"status": "error", "message": "Permission denied on data directory"}

    except Exception as e:
        logger.error(f"Static files health check failed: {e}")
        return {"status": "error", "message": f"Health check failed: {e}"}
