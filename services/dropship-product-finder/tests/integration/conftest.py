"""Shared fixtures for integration tests to avoid external dependencies."""
from __future__ import annotations

import asyncio
from typing import Any, Dict

import pytest


class _FakeRedis:
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
        self._store.clear()


@pytest.fixture(scope="session")
def fake_redis() -> _FakeRedis:
    return _FakeRedis()


@pytest.fixture(scope="session", autouse=True)
def patch_redis(fake_redis: _FakeRedis) -> None:
    """Return the shared fake Redis client whenever redis.from_url is called."""

    import redis.asyncio as redis_async

    patcher = pytest.MonkeyPatch()
    patcher.setattr(redis_async, "from_url", lambda *args, **kwargs: fake_redis)
    yield
    patcher.undo()


@pytest.fixture(scope="session", autouse=True)
def patch_ebay_auth() -> None:
    """Stub the eBay auth token request to avoid real network calls."""

    from itertools import count

    token_counter = count(1)

    async def fake_request_access_token(self) -> Dict[str, Any]:
        return {
            "access_token": f"test-token-{next(token_counter)}",
            "expires_in": 7200,
        }

    patcher = pytest.MonkeyPatch()
    patcher.setattr(
        "services.ebay_auth_api_client.EbayAuthAPIClient.request_access_token",
        fake_request_access_token,
    )
    yield
    patcher.undo()


@pytest.fixture(scope="session", autouse=True)
def patch_ebay_browse() -> None:
    """Stub Browse API requests with deterministic data."""

    async def fake_make_request_with_retry(self, url: str, headers: dict, params: dict) -> Dict[str, Any]:
        if "item_summary/search" in url:
            query = (params.get("q") or "test").strip() or "search"
            limit = int(params.get("limit", 5))
            limit = max(1, min(limit, 5))
            summaries = []
            for idx in range(limit):
                item_id = f"{query.replace(' ', '-')}-{idx+1}"
                summaries.append(
                    {
                        "itemId": item_id,
                        "title": f"{query.title()} Product {idx+1}",
                        "itemWebUrl": f"https://example.com/items/{item_id}",
                        "image": {"imageUrl": f"https://example.com/images/{item_id}.jpg"},
                        "seller": {"username": "integration_seller"},
                    }
                )
            return {"itemSummaries": summaries}

        # Detailed item request
        item_id = url.rsplit("/", 1)[-1]
        detail = {
            "item": {
                "itemId": item_id,
                "title": f"Detailed {item_id}",
                "brand": "IntegrationBrand",
                "manufacturer": "IntegrationMaker",
                "itemWebUrl": f"https://example.com/items/{item_id}",
                "image": {"imageUrl": f"https://example.com/images/{item_id}.jpg"},
                "galleryInfo": {
                    "imageVariations": [
                        {"imageUrl": f"https://example.com/images/{item_id}_1.jpg"},
                        {"imageUrl": f"https://example.com/images/{item_id}_2.jpg"},
                    ]
                },
                "price": {"value": "99.99", "currency": "USD"},
                "shippingOptions": [
                    {
                        "shippingType": "STANDARD",
                        "shippingCost": {"value": "5.00", "currency": "USD"},
                    }
                ],
                "epid": f"EPID-{item_id}",
            }
        }
        return detail

    patcher = pytest.MonkeyPatch()
    patcher.setattr(
        "services.ebay_browse_api_client.EbayBrowseApiClient._make_request_with_retry",
        fake_make_request_with_retry,
    )
    yield
    patcher.undo()


@pytest.fixture(scope="session", autouse=True)
def fast_asyncio_sleep() -> None:
    """Speed up integration tests by shortening sleeps."""

    original_sleep = asyncio.sleep
    patcher = pytest.MonkeyPatch()

    async def immediate_sleep(_seconds: float, *_, **__) -> None:  # pragma: no cover - timing helper
        await original_sleep(0)

    patcher.setattr(asyncio, "sleep", immediate_sleep)
    yield
    patcher.undo()


@pytest.fixture(autouse=True)
def reset_fake_redis(fake_redis: _FakeRedis) -> None:
    """Clear fake Redis state between tests to avoid cross-test leakage."""
    fake_redis._store.clear()
