import functools
from common_py.logging_config import configure_logging
from contracts.validator import validator

logger = configure_logging("vision-embedding:decorators")

def validate_event(schema_name):
    """Decorator to validate event data against a schema."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                event_data = (
                    args[1]
                    if len(args) > 1
                    else kwargs.get("event_data")
                )
                if not event_data:
                    raise ValueError("Event data not found in arguments")

                validator.validate_event(schema_name, event_data)
                return await func(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - logging path
                logger.error(
                    "Validation failed",
                    schema=schema_name,
                    error=str(exc),
                )
                raise

        return wrapper

    return decorator

def handle_errors(func):
    """Decorator to handle and log errors in event handlers."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - logging path
            logger.error(
                "Handler raised an exception",
                handler=func.__name__,
                error=str(exc),
            )
            raise

    return wrapper
