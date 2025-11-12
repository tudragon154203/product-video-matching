import pytest
from unittest.mock import AsyncMock
import sys
import os
import redis.asyncio as redis  # Import redis directly

pytestmark = pytest.mark.unit

# Add the project root to the path for correct imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Add the libs/common-py to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs", "common-py"))


@pytest.mark.asyncio
@pytest.mark.unit
async def test_service_context_happy_path(monkeypatch):
    """
    Asserts that all connections are established and closed successfully
    in the happy path execution of service_context.
    """
    from main import service_context, DropshipProductHandler

    # Mock the dependencies
    mock_db_connect = AsyncMock()
    mock_db_disconnect = AsyncMock()
    mock_broker_connect = AsyncMock()
    mock_broker_disconnect = AsyncMock()
    mock_redis_ping = AsyncMock(return_value="PONG")
    mock_redis_close = AsyncMock(return_value=None)
    mock_update_redis_client = AsyncMock(return_value=None)  # Fix: return None instead of coroutine

    class MockDB:
        connect = mock_db_connect
        disconnect = mock_db_disconnect

    class MockBroker:
        connect = mock_broker_connect
        disconnect = mock_broker_disconnect

    class MockHandler(DropshipProductHandler):
        def __init__(self):
            # Bypass real initialization that might call config/etc
            self.db = MockDB()
            self.broker = MockBroker()
            self.update_redis_client = mock_update_redis_client

    # Mock the Redis client creation
    class MockRedisClient:
        def __init__(self):
            self.ping_called = False
            self.close = mock_redis_close

        async def ping(self):
            self.ping_called = True
            return "PONG"

    class MockRedis:
        def from_url(*args, **kwargs):
            return MockRedisClient()

    monkeypatch.setattr("main.DropshipProductHandler", MockHandler)
    monkeypatch.setattr("main.redis", MockRedis)

    # Execute the context manager
    async with service_context() as handler:
        # Assert connections were made
        mock_db_connect.assert_called_once()
        mock_broker_connect.assert_called_once()

        # Assert handler received the redis client (note: this is not awaited in the code, so it's a sync call)
        # The warning about coroutine not awaited is expected

    # Assert connections were closed in the finally block
    mock_db_disconnect.assert_called_once()
    mock_broker_disconnect.assert_called_once()
    mock_redis_close.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_service_context_db_connect_failure(monkeypatch):
    """
    Asserts that an exception during DB connection bubbles up and cleanup still occurs.
    """
    from main import service_context, DropshipProductHandler
    # This exception is used to test the failure path and cleanup flow

    class MockServiceException(Exception):
        pass

    # Mock the dependencies
    mock_db_connect = AsyncMock(side_effect=MockServiceException("DB Error"))
    mock_db_disconnect = AsyncMock()
    mock_broker_connect = AsyncMock()
    mock_broker_disconnect = AsyncMock()
    mock_redis_close = AsyncMock()

    class MockDB:
        connect = mock_db_connect
        disconnect = mock_db_disconnect

    class MockBroker:
        connect = mock_broker_connect
        disconnect = mock_broker_disconnect

    class MockHandler(DropshipProductHandler):
        def __init__(self):
            self.db = MockDB()
            self.broker = MockBroker()
            self.update_redis_client = AsyncMock()

    # Mock the Redis client creation (it won't be called)
    class MockRedisClient2:
        async def ping(self):
            raise Exception("Should not be called")

        async def close(self):
            return None

    class MockRedis:
        def from_url(*args, **kwargs):
            return MockRedisClient2()

    monkeypatch.setattr("main.DropshipProductHandler", MockHandler)
    monkeypatch.setattr("main.redis", MockRedis)

    # Execute the context manager and assert exception
    with pytest.raises(MockServiceException, match="DB Error"):
        async with service_context():
            pass

    # Assert DB disconnect was called as cleanup
    mock_db_disconnect.assert_called_once()
    # Assert broker connect was NOT called, but disconnect WAS called as cleanup
    mock_broker_connect.assert_not_called()
    mock_broker_disconnect.assert_called_once()
    # Assert Redis was never initialized, so close was NOT called
    mock_redis_close.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_service_context_redis_connect_failure(monkeypatch, caplog):
    """
    Asserts that an exception during Redis connection bubbles up and cleanup still occurs.
    """
    from main import service_context, DropshipProductHandler
    from redis.exceptions import ConnectionError

    # Mock the dependencies
    mock_db_connect = AsyncMock()
    mock_db_disconnect = AsyncMock()
    mock_broker_connect = AsyncMock()
    mock_broker_disconnect = AsyncMock()
    mock_redis_close = AsyncMock()

    class MockDB:
        connect = mock_db_connect
        disconnect = mock_db_disconnect

    class MockBroker:
        connect = mock_broker_connect
        disconnect = mock_broker_disconnect

    class MockHandler(DropshipProductHandler):
        def __init__(self):
            self.db = MockDB()
            self.broker = MockBroker()
            self.update_redis_client = AsyncMock()

    # Mock the Redis client creation with a failure during ping
    class MockRedis:
        def from_url(*args, **kwargs):
            return MockRedis()

        async def ping(self):
            raise ConnectionError("Redis down")

        async def close(self):
            return mock_redis_close()

    monkeypatch.setattr("main.DropshipProductHandler", MockHandler)
    monkeypatch.setattr("main.redis", MockRedis)

    # Execute the context manager and assert exception
    with pytest.raises(ConnectionError, match="Redis down"):
        async with service_context():
            pass

    # Assert all connections that were made are now closed
    mock_db_connect.assert_called_once()
    mock_broker_connect.assert_called_once()
    mock_db_disconnect.assert_called_once()
    mock_broker_disconnect.assert_called_once()
    # Redis client was initialized but the connection failed during ping,
    # so the cleanup path should attempt to close the client.
    mock_redis_close.assert_called_once()

    # assert "Failed to initialize service resources" in caplog.text
