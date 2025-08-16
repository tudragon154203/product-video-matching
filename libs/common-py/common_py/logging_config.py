import logging
import sys
from typing import Any, Dict, Optional


class ContextLogger:
    """Thin wrapper around stdlib logger that supports structured kwargs.

    Allows calls like `logger.info("msg", job_id=123, error=str(e))` by
    appending key=value pairs to the message and avoiding TypeError from
    stdlib Logger._log rejecting unknown kwargs.
    """

    def __init__(self, base: logging.Logger):
        self._base = base

    @property
    def name(self) -> str:
        return self._base.name

    def setLevel(self, level: int) -> None:
        self._base.setLevel(level)

    # Internal helper to format message and split supported kwargs
    def _prepare(self, msg: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        # Extract stdlib-supported kwargs
        std_kwargs: Dict[str, Any] = {}
        for key in ("exc_info", "stack_info", "stacklevel", "extra"):
            if key in kwargs:
                std_kwargs[key] = kwargs.pop(key)
        if kwargs:
            parts = ", ".join(f"{k}={kwargs[k]}" for k in kwargs)
            msg = f"{msg} | {parts}"
        return {"msg": msg, "std": std_kwargs}

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        prepared = self._prepare(msg, kwargs)
        self._base.debug(prepared["msg"], *args, **prepared["std"])  # type: ignore[arg-type]

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        prepared = self._prepare(msg, kwargs)
        self._base.info(prepared["msg"], *args, **prepared["std"])  # type: ignore[arg-type]

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        prepared = self._prepare(msg, kwargs)
        self._base.warning(prepared["msg"], *args, **prepared["std"])  # type: ignore[arg-type]

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        prepared = self._prepare(msg, kwargs)
        self._base.error(prepared["msg"], *args, **prepared["std"])  # type: ignore[arg-type]

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        # Ensure exc_info=True unless explicitly provided
        kwargs.setdefault("exc_info", True)
        prepared = self._prepare(msg, kwargs)
        self._base.exception(prepared["msg"], *args, **prepared["std"])  # type: ignore[arg-type]

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        prepared = self._prepare(msg, kwargs)
        self._base.critical(prepared["msg"], *args, **prepared["std"])  # type: ignore[arg-type]


def configure_logging(service_name: str, log_level: str = "INFO") -> ContextLogger:
    """Configure logging and return a ContextLogger that accepts kwargs.

    Usage:
        logger = configure_logging("main-api")
        logger.info("Started", job_id=job_id)
        logger.error("Failure", error=str(e))
    """

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    base = logging.getLogger(service_name)
    base.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    return ContextLogger(base)
