"""
Static file logging middleware for monitoring static file requests.
"""

import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable


logger = logging.getLogger(__name__)


class StaticFileLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log static file requests with request_id."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Log static file requests and responses.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler in the chain
            
        Returns:
            The HTTP response
        """
        if scope["type"] == "http":
            start_time = time.time()
            request_id = request.headers.get("x-request-id", "unknown")
            
            logger.info(
                f"Static file request - Method: {request.method}, "
                f"Path: {request.url.path}, "
                f"Request ID: {request_id}"
            )
            
            response = await call_next(request)
            
            process_time = time.time() - start_time
            logger.info(
                f"Static file response - Status: {response.status_code}, "
                f"Process Time: {process_time:.3f}s, "
                f"Request ID: {request_id}"
            )
            
            return response
        else:
            return await call_next(request)