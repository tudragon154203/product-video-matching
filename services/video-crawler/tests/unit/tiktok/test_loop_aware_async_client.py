import asyncio
from types import SimpleNamespace

import pytest

from platform_crawler.tiktok.loop_aware_async_client import LoopAwareAsyncClient


class DummyAsyncClient:
    def __init__(self):
        self.is_closed = False
        self.closed_via_aclose = False
        self.closed_via_close = False

    async def aclose(self):
        self.is_closed = True
        self.closed_via_aclose = True

    def close(self):
        self.is_closed = True
        self.closed_via_close = True


@pytest.fixture
def logger_stub():
    return SimpleNamespace(debug=lambda *args, **kwargs: None)


@pytest.mark.asyncio
async def test_get_client_reuses_same_loop(logger_stub):
    factory_calls = 0

    def factory():
        nonlocal factory_calls
        factory_calls += 1
        return DummyAsyncClient()

    manager = LoopAwareAsyncClient(factory, logger_stub)

    client_one = manager.get_client()
    client_two = manager.get_client()

    assert client_one is client_two
    assert factory_calls == 1

    await manager.close()


@pytest.mark.asyncio
async def test_close_closes_client_on_same_loop(logger_stub):
    client = DummyAsyncClient()

    manager = LoopAwareAsyncClient(lambda: client, logger_stub)

    _ = manager.get_client()
    await manager.close()

    assert client.closed_via_aclose is True
    assert manager._client is None  # type: ignore[attr-defined]
    assert manager._loop is None  # type: ignore[attr-defined]


def test_get_client_recreates_after_loop_closed(logger_stub):
    created_clients = []

    def factory():
        client = DummyAsyncClient()
        created_clients.append(client)
        return client

    manager = LoopAwareAsyncClient(factory, logger_stub)

    legacy_loop = asyncio.new_event_loop()
    try:
        async def init_client():
            return manager.get_client()

        old_client = legacy_loop.run_until_complete(init_client())
    finally:
        legacy_loop.close()

    new_client = manager.get_client()

    assert new_client is not old_client
    assert old_client.closed_via_close is True

    asyncio.run(manager.close())


def test_get_client_recreates_when_loop_changes(logger_stub):
    created_clients = []

    def factory():
        client = DummyAsyncClient()
        created_clients.append(client)
        return client

    manager = LoopAwareAsyncClient(factory, logger_stub)

    legacy_loop = asyncio.new_event_loop()

    async def init_client():
        return manager.get_client()

    old_client = legacy_loop.run_until_complete(init_client())

    replacement_loop = asyncio.new_event_loop()

    try:
        async def acquire():
            return manager.get_client()

        new_client = replacement_loop.run_until_complete(acquire())
    finally:
        replacement_loop.close()

    assert new_client is not old_client

    # Allow the legacy loop to process the scheduled close task.
    try:
        legacy_loop.run_until_complete(asyncio.sleep(0))
        legacy_loop.run_until_complete(asyncio.sleep(0))
    finally:
        legacy_loop.close()

    assert old_client.closed_via_aclose is True

    asyncio.run(manager.close())
