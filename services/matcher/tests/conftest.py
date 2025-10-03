"""Shared pytest configuration for matcher service tests."""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

TESTS_DIR = Path(__file__).resolve().parent
SERVICE_ROOT = TESTS_DIR.parent
REPO_ROOT = SERVICE_ROOT.parent.parent
LIBS_ROOT = REPO_ROOT / "libs"
COMMON_PY_ROOT = LIBS_ROOT / "common-py"

for candidate in (SERVICE_ROOT, LIBS_ROOT, COMMON_PY_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)


try:  # pragma: no cover - runtime configuration
    import asyncpg  # type: ignore  # noqa: F401 - imported for side effects
except ImportError:  # pragma: no cover - executed in lightweight test envs
    async def _create_pool(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("asyncpg is not installed in the test environment")

    sys.modules["asyncpg"] = SimpleNamespace(Pool=object, create_pool=_create_pool)


try:  # pragma: no cover - runtime configuration
    import aio_pika  # type: ignore  # noqa: F401 - imported for side effects
except ImportError:  # pragma: no cover - executed in lightweight test envs
    class _DeliveryMode:
        PERSISTENT = "PERSISTENT"

    class _ExchangeType:
        TOPIC = "TOPIC"

    class _Message:
        def __init__(self, *args, **kwargs) -> None:
            self.body = args[0] if args else b""

    async def _connect_robust(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("aio_pika is not installed in the test environment")

    sys.modules["aio_pika"] = SimpleNamespace(
        ExchangeType=_ExchangeType,
        DeliveryMode=_DeliveryMode,
        Exchange=object,
        IncomingMessage=object,
        Message=_Message,
        connect_robust=_connect_robust,
    )


try:  # pragma: no cover - runtime configuration
    from pydantic import BaseModel  # type: ignore  # noqa: F401
except ImportError:  # pragma: no cover - executed in lightweight test envs
    class _BaseModel:
        def __init__(self, **data) -> None:
            for key, value in data.items():
                setattr(self, key, value)

        def dict(self) -> dict[str, object]:
            return self.__dict__.copy()

    def _field(default=..., **kwargs):  # type: ignore[no-untyped-def]
        return default

    sys.modules["pydantic"] = SimpleNamespace(BaseModel=_BaseModel, Field=_field)


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """Execute ``async def`` tests without requiring external plugins."""

    test_func = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_func):
        testargs = {
            name: pyfuncitem.funcargs[name]
            for name in pyfuncitem._fixtureinfo.argnames  # type: ignore[attr-defined]
        }
        asyncio.run(test_func(**testargs))
        return True
    return None
