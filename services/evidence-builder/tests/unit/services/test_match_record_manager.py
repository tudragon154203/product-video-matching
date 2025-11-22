"""Unit tests for MatchRecordManager."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from services.match_record_manager import MatchRecordManager


@pytest.fixture
def mock_db():
    """Mock database manager."""
    db = MagicMock()
    db.fetch_val = AsyncMock()
    db.fetch_one = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def manager(mock_db):
    """Create MatchRecordManager instance."""
    return MatchRecordManager(mock_db)


@pytest.mark.asyncio
async def test_is_evidence_processed_returns_true(manager, mock_db):
    """Test checking if evidence is processed returns True."""
    mock_db.fetch_val.return_value = True
    
    result = await manager.is_evidence_processed("match_123")
    
    assert result is True
    mock_db.fetch_val.assert_called_once()


@pytest.mark.asyncio
async def test_is_evidence_processed_returns_false(manager, mock_db):
    """Test checking if evidence is processed returns False."""
    mock_db.fetch_val.return_value = False
    
    result = await manager.is_evidence_processed("match_123")
    
    assert result is False


@pytest.mark.asyncio
async def test_mark_evidence_processed(manager, mock_db):
    """Test marking evidence as processed."""
    await manager.mark_evidence_processed("match_123")
    
    mock_db.execute.assert_called_once()
    call_args = mock_db.execute.call_args[0]
    assert "processed_events" in call_args[0]
    assert call_args[2] == "match_123"


@pytest.mark.asyncio
async def test_update_match_record_and_log(manager, mock_db):
    """Test updating match record with evidence path."""
    await manager.update_match_record_and_log(
        "job_123",
        "prod_456",
        "vid_789",
        "/app/data/evidence/match.jpg"
    )
    
    mock_db.execute.assert_called_once()
    call_args = mock_db.execute.call_args[0]
    assert "UPDATE matches" in call_args[0]
    assert call_args[1] == "/app/data/evidence/match.jpg"
    assert call_args[2] == "prod_456"
    assert call_args[3] == "vid_789"
    assert call_args[4] == "job_123"


@pytest.mark.asyncio
async def test_get_image_info_success(manager, mock_db):
    """Test getting image info successfully."""
    mock_db.fetch_one.return_value = {
        "local_path": "/app/data/images/img.jpg",
        "kp_blob_path": "/app/data/keypoints/img.pkl"
    }
    
    result = await manager.get_image_info("img_123")
    
    assert result is not None
    assert result["local_path"] == "/app/data/images/img.jpg"
    assert result["kp_blob_path"] == "/app/data/keypoints/img.pkl"
    mock_db.fetch_one.assert_called_once()


@pytest.mark.asyncio
async def test_get_image_info_not_found(manager, mock_db):
    """Test getting image info when not found."""
    mock_db.fetch_one.return_value = None
    
    result = await manager.get_image_info("img_123")
    
    assert result is None


@pytest.mark.asyncio
async def test_get_frame_info_success(manager, mock_db):
    """Test getting frame info successfully."""
    mock_db.fetch_one.return_value = {
        "local_path": "/app/data/frames/frame.png",
        "kp_blob_path": "/app/data/keypoints/frame.pkl"
    }
    
    result = await manager.get_frame_info("frame_123")
    
    assert result is not None
    assert result["local_path"] == "/app/data/frames/frame.png"
    assert result["kp_blob_path"] == "/app/data/keypoints/frame.pkl"
    mock_db.fetch_one.assert_called_once()


@pytest.mark.asyncio
async def test_get_frame_info_not_found(manager, mock_db):
    """Test getting frame info when not found."""
    mock_db.fetch_one.return_value = None
    
    result = await manager.get_frame_info("frame_123")
    
    assert result is None


@pytest.mark.asyncio
async def test_get_match_counts_with_matches(manager, mock_db):
    """Test getting match counts with matches."""
    mock_db.fetch_val.side_effect = [10, 7]  # 10 total, 7 with evidence
    
    total, with_evidence = await manager.get_match_counts("job_123")
    
    assert total == 10
    assert with_evidence == 7
    assert mock_db.fetch_val.call_count == 2


@pytest.mark.asyncio
async def test_get_match_counts_no_matches(manager, mock_db):
    """Test getting match counts with no matches."""
    mock_db.fetch_val.side_effect = [0, 0]
    
    total, with_evidence = await manager.get_match_counts("job_123")
    
    assert total == 0
    assert with_evidence == 0


@pytest.mark.asyncio
async def test_get_match_counts_handles_none(manager, mock_db):
    """Test getting match counts handles None values."""
    mock_db.fetch_val.side_effect = [None, None]
    
    total, with_evidence = await manager.get_match_counts("job_123")
    
    assert total == 0
    assert with_evidence == 0
