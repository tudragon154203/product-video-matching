import logging
import sys
import json
import os
import inspect
from pathlib import Path
from typing import Any, Dict, Optional
from contextvars import ContextVar, copy_context


# Define a ContextVar for correlation_id
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        # Add correlation_id if present in the context
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_record["correlation_id"] = correlation_id

        if hasattr(record, "extra_kwargs"):
            log_record.update(record.extra_kwargs)
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_record["stack_info"] = self.formatStack(record.stack_info)
        return json.dumps(log_record)


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
            # Include extra kwargs in the message for default format
            extra_parts = []
            for key, value in kwargs.items():
                extra_parts.append(f"{key}={value}")
            if extra_parts:
                msg = f"{msg} - {' - '.join(extra_parts)}"
            std_kwargs["extra"] = {"extra_kwargs": kwargs}  # Still pass for JSON format
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


def _standardize_logger_name(name: str) -> str:
    """Ensure logger name follows `microservice:file` when possible.

    If the provided name already contains a colon, it is returned unchanged.
    Otherwise, attempt to infer microservice and file from the caller's path.
    Falls back to the original name if inference fails.
    """
    try:
        if ":" in name:
            return name

        # Inspect call stack to find the first external frame
        frame = inspect.currentframe()
        if frame is None:
            return name
        caller = frame.f_back
        # Walk back until we leave this module
        this_file = __file__
        while caller and caller.f_code.co_filename == this_file:
            caller = caller.f_back
        if not caller:
            return name

        p = Path(caller.f_code.co_filename).resolve()
        parts = p.parts
        if "services" in parts:
            i = parts.index("services")
            micro = parts[i + 1]
            file_part = p.stem if p.name != "__init__.py" else p.parent.name
            return f"{micro}:{file_part}"
        if "libs" in parts:
            i = parts.index("libs")
            micro = parts[i + 1]
            file_part = p.stem if p.name != "__init__.py" else p.parent.name
            return f"{micro}:{file_part}"
        if "scripts" in parts:
            file_part = p.stem if p.name != "__init__.py" else p.parent.name
            return f"scripts:{file_part}"
        return name
    except Exception:
        return name


def configure_logging(
    service_name: str,
    log_level: str = "INFO",
    log_format: Optional[str] = None,
) -> ContextLogger:
    """Configure logging and return a ContextLogger that accepts kwargs.

    Usage:
        logger = configure_logging("service:file")
        logger.info("Started", job_id=job_id)
        logger.error("Failure", error=str(e))
    """
    # Standardize logger name to the `service:file` format when possible
    service_name = _standardize_logger_name(service_name)
    if log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            log_format or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Remove any existing handlers to prevent duplicate logs in case of re-configuration
    for handler in logging.getLogger(service_name).handlers[:]:
        logging.getLogger(service_name).removeHandler(handler)
        handler.close()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    base = logging.getLogger(service_name)
    base.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    base.addHandler(handler)
    base.propagate = False  # Prevent logs from being duplicated by the root logger

    return ContextLogger(base)


def set_correlation_id(correlation_id: Optional[str]) -> None:
    """Sets the correlation ID for the current context."""
    correlation_id_var.set(correlation_id)
