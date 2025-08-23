from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from uuid import uuid4
from datetime import datetime
from typing import List, Dict, Any


class BaseException(Exception):
    def __init__(self, message: str, error_code: str, status_code: int = 500, details: List[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or []
        super().__init__(self.message)


class ResourceNotFound(BaseException):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            f"{resource} with id '{resource_id}' not found",
            "RESOURCE_NOT_FOUND",
            404
        )


class ValidationError(BaseException):
    def __init__(self, field: str, message: str):
        super().__init__(
            f"Validation error in field '{field}': {message}",
            "VALIDATION_ERROR",
            422
        )


class DatabaseError(BaseException):
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            message,
            "DATABASE_ERROR",
            500
        )


class BaseExceptionHandler:
    @staticmethod
    async def base_exception_handler(request: Request, exc: BaseException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "correlation_id": str(uuid4()),
                "error_code": exc.error_code,
                "message": exc.message,
                "timestamp": datetime.utcnow().isoformat(),
                "details": exc.details
            }
        )
    
    @staticmethod
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = []
        for error in exc.errors():
            details.append({
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        return JSONResponse(
            status_code=422,
            content={
                "correlation_id": str(uuid4()),
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "timestamp": datetime.utcnow().isoformat(),
                "details": details
            }
        )
    
    @staticmethod
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "correlation_id": str(uuid4()),
                "error_code": "HTTP_ERROR",
                "message": exc.detail,
                "timestamp": datetime.utcnow().isoformat(),
                "details": []
            }
        )