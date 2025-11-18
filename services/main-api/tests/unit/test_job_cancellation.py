import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.job.job_management_service import JobManagementService
from handlers.database_handler import DatabaseHandler
from handlers.broker_handler import BrokerHandler
from fastapi import HTTPException


@pytest.fixture
def mock_db_handler():
    return MagicMock(spec=DatabaseHandler)


@pytest.fixture
def mock_broker_handler():
    return MagicMock(spec=BrokerHandler)


@pytest.fixture
def job_management_service(mock_db_handler, mock_broker_handler):
    with patch('services.job.job_management_service.LLMService'), \
         patch('services.job.job_management_service.PromptService'):
        service = JobManagementService(mock_db_handler, mock_broker_handler)
        return service


@pytest.mark.asyncio
async def test_cancel_job_success(job_management_service, mock_db_handler, mock_broker_handler):
    """Test successful job cancellation"""
    job_id = "test-job-123"
    
    # Mock job exists and is in progress
    mock_db_handler.get_job = AsyncMock(return_value={
        "job_id": job_id,
        "phase": "collection",
        "query": "test query"
    })
    
    mock_db_handler.cancel_job = AsyncMock()
    mock_db_handler.get_job_cancellation_info = AsyncMock(return_value={
        "cancelled_at": "2025-11-18T10:00:00",
        "cancelled_by": "test_user",
        "reason": "user_request",
        "notes": "Test cancellation"
    })
    
    mock_broker_handler.purge_job_messages = AsyncMock(return_value=5)
    mock_broker_handler.publish_job_cancelled = AsyncMock()
    
    # Execute
    result = await job_management_service.cancel_job(
        job_id=job_id,
        reason="user_request",
        notes="Test cancellation",
        cancelled_by="test_user"
    )
    
    # Verify
    assert result["job_id"] == job_id
    assert result["phase"] == "cancelled"
    assert result["reason"] == "user_request"
    mock_db_handler.cancel_job.assert_called_once()
    mock_broker_handler.purge_job_messages.assert_called_once_with(job_id)
    mock_broker_handler.publish_job_cancelled.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_job_not_found(job_management_service, mock_db_handler):
    """Test cancelling non-existent job returns 404"""
    job_id = "nonexistent-job"
    
    mock_db_handler.get_job = AsyncMock(return_value=None)
    
    with pytest.raises(HTTPException) as exc_info:
        await job_management_service.cancel_job(job_id=job_id)
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_cancel_job_idempotent(job_management_service, mock_db_handler, mock_broker_handler):
    """Test cancelling already cancelled job is idempotent"""
    job_id = "test-job-123"
    
    mock_db_handler.get_job = AsyncMock(return_value={
        "job_id": job_id,
        "phase": "cancelled",
        "query": "test query"
    })
    
    mock_db_handler.get_job_cancellation_info = AsyncMock(return_value={
        "cancelled_at": "2025-11-18T10:00:00",
        "cancelled_by": "test_user",
        "reason": "user_request",
        "notes": None
    })
    
    result = await job_management_service.cancel_job(job_id=job_id)
    
    assert result["job_id"] == job_id
    assert result["phase"] == "cancelled"
    mock_db_handler.cancel_job.assert_not_called()
    mock_broker_handler.purge_job_messages.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_completed_job(job_management_service, mock_db_handler):
    """Test cancelling completed job returns current state"""
    job_id = "test-job-123"
    
    mock_db_handler.get_job = AsyncMock(return_value={
        "job_id": job_id,
        "phase": "completed",
        "query": "test query"
    })
    
    result = await job_management_service.cancel_job(job_id=job_id)
    
    assert result["job_id"] == job_id
    assert result["phase"] == "completed"
    assert "already completed" in result["reason"]


@pytest.mark.asyncio
async def test_delete_job_success(job_management_service, mock_db_handler, mock_broker_handler):
    """Test successful job deletion"""
    job_id = "test-job-123"
    
    mock_db_handler.get_job = AsyncMock(side_effect=[
        {"job_id": job_id, "phase": "completed", "deleted_at": None},
        {"job_id": job_id, "phase": "completed", "deleted_at": "2025-11-18T10:00:00"}
    ])
    
    mock_db_handler.is_job_active = AsyncMock(return_value=False)
    mock_db_handler.delete_job_data = AsyncMock()
    mock_broker_handler.publish_job_deleted = AsyncMock()
    
    result = await job_management_service.delete_job(job_id=job_id)
    
    assert result["job_id"] == job_id
    assert result["status"] == "deleted"
    mock_db_handler.delete_job_data.assert_called_once()
    mock_broker_handler.publish_job_deleted.assert_called_once()


@pytest.mark.asyncio
async def test_delete_active_job_without_force(job_management_service, mock_db_handler):
    """Test deleting active job without force flag raises 409"""
    job_id = "test-job-123"
    
    mock_db_handler.get_job = AsyncMock(return_value={
        "job_id": job_id,
        "phase": "collection",
        "deleted_at": None
    })
    
    mock_db_handler.is_job_active = AsyncMock(return_value=True)
    
    with pytest.raises(HTTPException) as exc_info:
        await job_management_service.delete_job(job_id=job_id, force=False)
    
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_delete_active_job_with_force(job_management_service, mock_db_handler, mock_broker_handler):
    """Test deleting active job with force flag cancels then deletes"""
    job_id = "test-job-123"
    
    mock_db_handler.get_job = AsyncMock(side_effect=[
        {"job_id": job_id, "phase": "collection", "deleted_at": None},
        {"job_id": job_id, "phase": "collection", "deleted_at": None},
        {"job_id": job_id, "phase": "cancelled", "deleted_at": "2025-11-18T10:00:00"}
    ])
    
    mock_db_handler.is_job_active = AsyncMock(return_value=True)
    mock_db_handler.cancel_job = AsyncMock()
    mock_db_handler.get_job_cancellation_info = AsyncMock(return_value={
        "cancelled_at": "2025-11-18T10:00:00",
        "cancelled_by": "test_user",
        "reason": "deletion_requested",
        "notes": None
    })
    mock_db_handler.delete_job_data = AsyncMock()
    
    mock_broker_handler.purge_job_messages = AsyncMock(return_value=3)
    mock_broker_handler.publish_job_cancelled = AsyncMock()
    mock_broker_handler.publish_job_deleted = AsyncMock()
    
    result = await job_management_service.delete_job(job_id=job_id, force=True)
    
    assert result["job_id"] == job_id
    assert result["status"] == "deleted"
    mock_db_handler.cancel_job.assert_called_once()
    mock_db_handler.delete_job_data.assert_called_once()
