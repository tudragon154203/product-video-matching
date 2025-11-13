"""Shared fixtures for dropship-product-finder integration tests."""

from __future__ import annotations

from typing import Dict

import pytest


class InMemoryRedis:
    """Minimal async Redis replacement for integration tests."""

    def __init__(self) -> None:
        self._store: Dict[str, str] = {}

    async def setex(self, key: str, ttl: int, value: str) -> None:  # pragma: no cover - simple storage
        self._store[key] = value

    async def set(self, key: str, value: str) -> None:  # pragma: no cover - simple storage
        self._store[key] = value

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def delete(self, key: str) -> None:  # pragma: no cover - simple storage
        self._store.pop(key, None)

    async def ping(self) -> bool:  # pragma: no cover - simple storage
        return True

    async def close(self) -> None:  # pragma: no cover - simple storage
        self.clear()

    def clear(self) -> None:  # pragma: no cover - simple storage
        self._store.clear()


@pytest.fixture(scope="session")
def redis_client() -> InMemoryRedis:
    """Shared in-memory Redis client for integration tests."""

    return InMemoryRedis()


@pytest.fixture(scope="session", autouse=True)
def patch_redis() -> None:
    """Return the shared fake Redis client whenever redis.from_url is called."""

    import redis.asyncio as redis_async

    # Create a shared InMemoryRedis instance for the patch
    shared_redis = InMemoryRedis()

    patcher = pytest.MonkeyPatch()
    patcher.setattr(redis_async, "from_url", lambda *args, **kwargs: shared_redis)
    yield
    patcher.undo()


@pytest.fixture(autouse=True)
def reset_redis(redis_client: InMemoryRedis) -> None:
    """Clear in-memory Redis state between tests to avoid cross-test leakage."""

    redis_client.clear()
