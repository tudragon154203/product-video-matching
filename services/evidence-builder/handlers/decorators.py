"""Reusable decorators for evidence builder handlers."""

import functools
from typing import Any, Awaitable, Callable, TypeVar, cast

from common_py.logging_config import configure_logging
from contracts.validator import validator

logger = configure_logging("evidence-builder:decorators")

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def validate_event(schema_name: str) -> Callable[[F], F]:
    """Validate handler arguments against the configured schema."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any):
            event_data = args[1] if len(args) > 1 else kwargs.get("event_data")
            if event_data is None:
                raise ValueError("Event data not found in arguments")

            validator.validate_event(schema_name, event_data)
            return await func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator


def handle_errors(func: F) -> F:
    """Log and re-raise errors from handler execution."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any):
        try:
            return await func(*args, **kwargs)
        # We intentionally log and propagate every unexpected error so the caller
        # can decide how to handle it while still capturing a stack trace.
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error in handler %s: %s", func.__name__, exc)
            raise

    return cast(F, wrapper)
