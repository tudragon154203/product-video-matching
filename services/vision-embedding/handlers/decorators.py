import functools
import structlog
from contracts.validator import validator

logger = structlog.get_logger()

def validate_event(schema_name):
    """Decorator to validate event data against a schema"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(event_data):
            try:
                validator.validate_event(schema_name, event_data)
                return await func(event_data)
            except Exception as e:
                logger.error(f"Validation failed for {schema_name}: {str(e)}")
                raise
        return wrapper
    return decorator

def handle_errors(func):
    """Decorator to handle and log errors in event handlers"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
    return wrapper