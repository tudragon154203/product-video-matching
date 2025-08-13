from fastapi import HTTPException
import structlog

# Create a logger instance
logger = structlog.get_logger()

def handle_errors(func):
    """Decorator to handle errors in FastAPI endpoints"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    return wrapper