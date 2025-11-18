import pytest
from unittest.mock import AsyncMock, MagicMock
from handlers.broker_handler import BrokerHandler


@pytest.fixture
def mock_broker():
    broker = MagicMock()
    broker.channel = MagicMock()
    return broker


@pytest.fixture
def broker_handler(mock_broker):
    return BrokerHandler(mock_broker)


@pytest.mark.asyncio
async def test_purge_job_messages_returns_zero(broker_handler):
    """Test that purge_job_messages returns 0 (simplified implementation)"""
    job_id = "test-job-123"
    
    result = await broker_handler.purge_job_messages(job_id)
    
    # Simplified implementation always returns 0
    # Actual purging relies on workers checking job.cancelled event
    assert result == 0


@pytest.mark.asyncio
async def test_purge_job_messages_does_not_raise(broker_handler):
    """Test that purge_job_messages completes without error"""
    job_id = "test-job-123"
    
    # Should complete without raising an exception
    result = await broker_handler.purge_job_messages(job_id)
    assert result == 0
