import functools
import structlog
from contracts.validator import validator

logger = structlog.get_logger()

def validate_event(schema_name):
    """Decorator to validate event data against a schema"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Extract event_data from args (position 1) or kwargs
                event_data = args[1] if len(args) > 1 else kwargs.get('event_data')
                if not event_data:
                    raise ValueError("Event data not found in arguments")
                
                validator.validate_event(schema_name, event_data)
                return await func(*args, **kwargs)
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