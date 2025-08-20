"""
Standardized error codes for the system
"""
from enum import Enum


class ErrorCode(Enum):
    """Standardized error codes"""
    
    # Retryable errors (1000-1999)
    NETWORK_TIMEOUT = "RETRY_1001"
    DATABASE_CONNECTION = "RETRY_1002"
    MESSAGE_BROKER_CONNECTION = "RETRY_1003"
    EXTERNAL_API_RATE_LIMIT = "RETRY_1004"
    TEMPORARY_SERVICE_UNAVAILABLE = "RETRY_1005"
    
    # Fatal errors (2000-2999)
    INVALID_EVENT_SCHEMA = "FATAL_2001"
    MISSING_REQUIRED_FILE = "FATAL_2002"
    AUTHENTICATION_FAILED = "FATAL_2003"
    AUTHORIZATION_DENIED = "FATAL_2004"
    INVALID_CONFIGURATION = "FATAL_2005"
    RESOURCE_NOT_FOUND = "FATAL_2006"
    
    # Business logic errors (3000-3999)
    INSUFFICIENT_KEYPOINTS = "BUSINESS_3001"
    EMBEDDING_EXTRACTION_FAILED = "BUSINESS_3002"
    NO_MATCHING_CANDIDATES = "BUSINESS_3003"
    SCORE_BELOW_THRESHOLD = "BUSINESS_3004"
    
    # System errors (4000-4999)
    OUT_OF_MEMORY = "SYSTEM_4001"
    DISK_SPACE_FULL = "SYSTEM_4002"
    GPU_NOT_AVAILABLE = "SYSTEM_4003"
    
    @property
    def is_retryable(self) -> bool:
        """Check if error is retryable"""
        return self.value.startswith("RETRY_")
    
    @property
    def is_fatal(self) -> bool:
        """Check if error is fatal"""
        return self.value.startswith("FATAL_")


class SystemError(Exception):
    """Base exception with error code"""
    
    def __init__(self, error_code: ErrorCode, message: str, details: dict = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(f"{error_code.value}: {message}")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging/serialization"""
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "details": self.details,
            "retryable": self.error_code.is_retryable,
            "fatal": self.error_code.is_fatal
        }


class RetryableError(SystemError):
    """Error that should be retried"""
    pass


class FatalError(SystemError):
    """Error that should not be retried"""
    pass


def create_error(error_code: ErrorCode, message: str, details: dict = None) -> SystemError:
    """Create appropriate error type based on error code"""
    if error_code.is_retryable:
        return RetryableError(error_code, message, details)
    else:
        return FatalError(error_code, message, details)