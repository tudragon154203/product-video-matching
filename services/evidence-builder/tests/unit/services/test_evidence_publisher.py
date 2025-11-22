"""Unit tests for EvidencePublisher."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from services.evidence_publisher import EvidencePublisher


@pytest.fixture
def mock_broker():
    """Mock message broker."""
    broker = MagicMock()
    broker.publish_event = AsyncMock()
    return broker


@pytest.fixture
def mock_db():
    """Mock database manager."""
    db = MagicMock()
    db.fetch_val = AsyncMock()
    db.fetch_one = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def publisher(mock_broker, mock_db):
    """Create EvidencePublisher instance."""
    return EvidencePublisher(mock_broker, mock_db)


@pytest.mark.asyncio
async def test_has_published_completion_returns_true(publisher, mock_db):
    """Test checking if completion has been published returns True."""
    mock_db.fetch_val.return_value = True
    
    result = await publisher.has_published_completion("job_123")
    
    assert result is True
    mock_db.fetch_val.assert_called_once()


@pytest.mark.asyncio
async def test_has_published_completion_returns_false(publisher, mock_db):
    """Test checking if completion has been published returns False."""
    mock_db.fetch_val.return_value = False
    
    result = await publisher.has_published_completion("job_123")
    
    assert result is False


@pytest.mark.asyncio
async def test_mark_completion_published(publisher, mock_db):
    """Test marking completion as published."""
    await publisher.mark_completion_published("job_123")
    
    mock_db.execute.assert_called_once()
    call_args = mock_db.execute.call_args[0]
    assert "processed_events" in call_args[0]
    assert call_args[2] == "job_123"


@pytest.mark.asyncio
async def test_check_and_publish_completion_already_published(publisher, mock_db):
    """Test check_and_publish_completion when already published."""
    mock_db.fetch_val.return_value = True
    
    await publisher.check_and_publish_completion("job_123")
    
    # Should not publish again
    assert mock_db.fetch_val.call_count == 1


@pytest.mark.asyncio
async def test_check_and_publish_completion_all_evidence_ready(publisher, mock_db, mock_broker):
    """Test publishing completion when all evidence is ready."""
    mock_db.fetch_val.side_effect = [False, 5, 5]  # not published, 5 total, 5 with evidence
    
    await publisher.check_and_publish_completion("job_123")
    
    mock_broker.publish_event.assert_called_once()
    call_args = mock_broker.publish_event.call_args
    event_name = call_args[0][0]
    event_data = call_args[0][1]
    assert event_name == "evidences.generation.completed"
    assert event_data["job_id"] == "job_123"
    assert "event_id" in event_data


@pytest.mark.asyncio
async def test_check_and_publish_completion_partial_evidence(publisher, mock_db, mock_broker):
    """Test not publishing when evidence is incomplete."""
    mock_db.fetch_val.side_effect = [False, 5, 3]  # not published, 5 total, 3 with evidence
    
    await publisher.check_and_publish_completion("job_123")
    
    # Should not publish
    mock_broker.publish_event.assert_not_called()


@pytest.mark.asyncio
async def test_check_and_publish_completion_no_matches(publisher, mock_db, mock_broker):
    """Test not publishing when there are no matches."""
    mock_db.fetch_val.side_effect = [False, 0, 0]  # not published, 0 total, 0 with evidence
    
    await publisher.check_and_publish_completion("job_123")
    
    # Should not publish for zero matches (handled by match_request_completed)
    mock_broker.publish_event.assert_not_called()


@pytest.mark.asyncio
async def test_handle_match_request_completed_zero_matches(publisher, mock_db, mock_broker):
    """Test handling match_request_completed with zero matches."""
    event_data = {"job_id": "job_123"}
    mock_db.fetch_val.side_effect = [0, False]  # 0 matches, not published
    
    await publisher.handle_match_request_completed(event_data, "corr_123")
    
    mock_broker.publish_event.assert_called_once()
    event_name = mock_broker.publish_event.call_args[0][0]
    assert event_name == "evidences.generation.completed"


@pytest.mark.asyncio
async def test_handle_match_request_completed_with_matches(publisher, mock_db, mock_broker):
    """Test handling match_request_completed with matches."""
    event_data = {"job_id": "job_123"}
    mock_db.fetch_val.return_value = 5  # 5 matches
    
    await publisher.handle_match_request_completed(event_data, "corr_123")
    
    # Should not publish, waiting for match.result events
    mock_broker.publish_event.assert_not_called()


@pytest.mark.asyncio
async def test_handle_match_request_completed_zero_matches_already_published(publisher, mock_db, mock_broker):
    """Test handling match_request_completed when already published."""
    event_data = {"job_id": "job_123"}
    mock_db.fetch_val.side_effect = [0, True]  # 0 matches, already published
    
    await publisher.handle_match_request_completed(event_data, "corr_123")
    
    # Should not publish again
    mock_broker.publish_event.assert_not_called()


@pytest.mark.asyncio
async def test_handle_match_request_completed_missing_job_id(publisher):
    """Test handling match_request_completed with missing job_id."""
    event_data = {}
    
    with pytest.raises(ValueError, match="missing job_id"):
        await publisher.handle_match_request_completed(event_data, "corr_123")
