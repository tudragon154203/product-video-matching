from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from uuid import uuid4
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import traceback

logger = logging.getLogger(__name__)


class BaseAPIException(Exception):
    """Base exception class for all API exceptions"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str, 
        status_code: int = 500, 
        details: Optional[List[Dict[str, Any]]] = None,
        correlation_id: Optional[str] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or []
        self.correlation_id = correlation_id or str(uuid4())
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response"""
        return {
            "correlation_id": self.correlation_id,
            "error_code": self.error_code,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }


class ResourceNotFound(BaseAPIException):
    """Exception raised when a requested resource is not found"""
    
    def __init__(self, resource: str, resource_id: str, correlation_id: Optional[str] = None):
        super().__init__(
            message=f"{resource} with id '{resource_id}' not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            correlation_id=correlation_id
        )
        self.resource = resource
        self.resource_id = resource_id


class ValidationError(BaseAPIException):
    """Exception raised for validation errors"""
    
    def __init__(self, field: str, message: str, correlation_id: Optional[str] = None):
        super().__init__(
            message=f"Validation error in field '{field}': {message}",
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=[{"field": field, "message": message}],
            correlation_id=correlation_id
        )
        self.field = field


class DatabaseError(BaseAPIException):
    """Exception raised for database operation errors"""
    
    def __init__(self, message: str = "Database operation failed", correlation_id: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=500,
            correlation_id=correlation_id
        )


class MCPError(BaseAPIException):
    """Exception raised for MCP server errors"""
    
    def __init__(self, message: str = "MCP server error", correlation_id: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="MCP_ERROR",
            status_code=500,
            correlation_id=correlation_id
        )


class ServiceError(BaseAPIException):
    """Exception raised for service layer errors"""
    
    def __init__(self, message: str, correlation_id: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="SERVICE_ERROR",
            status_code=500,
            correlation_id=correlation_id
        )


class AuthenticationError(BaseAPIException):
    """Exception raised for authentication errors"""
    
    def __init__(self, message: str = "Authentication failed", correlation_id: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
            correlation_id=correlation_id
        )


class AuthorizationError(BaseAPIException):
    """Exception raised for authorization errors"""
    
    def __init__(self, message: str = "Access denied", correlation_id: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
            correlation_id=correlation_id
        )


class ExceptionHandlers:
    """Collection of exception handlers for FastAPI application"""
    
    @staticmethod
    async def api_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
        """Handle custom API exceptions"""
        logger.error(
            "API exception occurred",
            extra={
                "correlation_id": exc.correlation_id,
                "error_code": exc.error_code,
                "error_message": exc.message,
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
                "details": exc.details
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )
    
    @staticmethod
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle FastAPI validation errors"""
        correlation_id = str(uuid4())
        details = []
        
        for error in exc.errors():
            details.append({
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input")
            })
        
        error_response = {
            "correlation_id": correlation_id,
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        }
        
        logger.warning(
            "Validation error occurred",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "validation_errors": details
            }
        )
        
        return JSONResponse(
            status_code=422,
            content=error_response
        )
    
    @staticmethod
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle FastAPI HTTP exceptions"""
        correlation_id = str(uuid4())
        
        error_response = {
            "correlation_id": correlation_id,
            "error_code": "HTTP_ERROR",
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "details": []
        }
        
        logger.warning(
            "HTTP exception occurred",
            extra={
                "correlation_id": correlation_id,
                "status_code": exc.status_code,
                "message": exc.detail,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response
        )
    
    @staticmethod
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions"""
        correlation_id = str(uuid4())
        
        error_response = {
            "correlation_id": correlation_id,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
            "details": []
        }
        
        logger.error(
            "Unexpected exception occurred",
            extra={
                "correlation_id": correlation_id,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc()
            }
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response
        )


def register_exception_handlers(app) -> None:
    """Register all exception handlers with FastAPI application"""
    app.add_exception_handler(BaseAPIException, ExceptionHandlers.api_exception_handler)
    app.add_exception_handler(RequestValidationError, ExceptionHandlers.validation_exception_handler)
    app.add_exception_handler(HTTPException, ExceptionHandlers.http_exception_handler)
    app.add_exception_handler(Exception, ExceptionHandlers.generic_exception_handler)