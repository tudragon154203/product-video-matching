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
                # Check kwargs first for explicit event_data
                event_data = kwargs.get("event_data")

                # If not in kwargs, check positional arguments
                if event_data is None:
                    # For instance methods, args[0] is self, event_data is args[1]
                    # For regular functions, event_data is args[0]
                    if len(args) >= 2:
                        event_data = args[1]  # instance method: self, event_data
                    elif len(args) == 1:
                        # Check if this is likely an instance method (has self parameter)
                        # We need to be more careful here - if the function is a method of a class
                        # and called with only one argument, it's probably self without event_data
                        # For regular functions, the single argument would be event_data
                        # We can try to detect this by checking if the argument has the same type as a class instance
                        arg = args[0]
                        # If this looks like an instance method call (object with __dict__), but no event_data
                        if hasattr(arg, '__dict__') and not isinstance(arg, (dict, list, str, int, float, bool)):
                            # This is likely an instance method call without event_data
                            event_data = None
                        else:
                            # This is likely a regular function call with event_data
                            event_data = args[0]

                if event_data is None:
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
