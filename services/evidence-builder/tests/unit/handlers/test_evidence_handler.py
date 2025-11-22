"""Unit tests for EvidenceHandler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from handlers.evidence_handler import EvidenceHandler


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = MagicMock()
    config.POSTGRES_DSN = "postgresql://test"
    config.BUS_BROKER = "amqp://test"
    config.DATA_ROOT = "/app/data"
    return config


@pytest.fixture
def handler(mock_config):
    """Create EvidenceHandler instance with mocked dependencies."""
    with patch('handlers.evidence_handler.DatabaseManager') as mock_db_class, \
         patch('handlers.evidence_handler.MessageBroker') as mock_broker_class, \
         patch('handlers.evidence_handler.EvidenceBuilderService') as mock_service_class, \
         patch('handlers.evidence_handler.config', mock_config):
        
        mock_db = MagicMock()
        mock_broker = MagicMock()
        mock_service = MagicMock()
        mock_service.handle_match_result = AsyncMock()
        mock_service.handle_match_request_completed = AsyncMock()
        
        mock_db_class.return_value = mock_db
        mock_broker_class.return_value = mock_broker
        mock_service_class.return_value = mock_service
        
        handler = EvidenceHandler()
        handler.service = mock_service
        
        return handler


@pytest.mark.asyncio
async def test_handle_match_result_success(handler):
    """Test handling match_result event successfully."""
    event_data = {
        "job_id": "job_123",
        "product_id": "prod_456",
        "video_id": "vid_789",
        "best_img_id": "img_001",
        "best_frame_id": "frame_001",
        "score": 0.95
    }
    
    await handler.handle_match_result(event_data, "corr_123")
    
    handler.service.handle_match_result.assert_called_once_with(
        event_data,
        "corr_123"
    )


@pytest.mark.asyncio
async def test_handle_match_request_completed_success(handler):
    """Test handling match_request_completed event successfully."""
    event_data = {
        "job_id": "job_123",
        "event_id": "evt_456"
    }
    
    await handler.handle_match_request_completed(event_data, "corr_123")
    
    handler.service.handle_match_request_completed.assert_called_once_with(
        event_data,
        "corr_123"
    )


@pytest.mark.asyncio
async def test_handle_match_result_with_error(handler):
    """Test handling match_result when service raises error."""
    event_data = {"job_id": "job_123"}
    handler.service.handle_match_result.side_effect = Exception("Database error")
    
    # The @handle_errors decorator should catch this
    with pytest.raises(Exception):
        await handler.handle_match_result(event_data, "corr_123")


@pytest.mark.asyncio
async def test_handle_match_request_completed_with_error(handler):
    """Test handling match_request_completed when service raises error."""
    event_data = {"job_id": "job_123"}
    handler.service.handle_match_request_completed.side_effect = Exception("Processing error")
    
    # The @handle_errors decorator should catch this
    with pytest.raises(Exception):
        await handler.handle_match_request_completed(event_data, "corr_123")


@pytest.mark.asyncio
async def test_handler_initialization(mock_config):
    """Test handler initializes with correct dependencies."""
    with patch('handlers.evidence_handler.DatabaseManager') as mock_db_class, \
         patch('handlers.evidence_handler.MessageBroker') as mock_broker_class, \
         patch('handlers.evidence_handler.EvidenceBuilderService') as mock_service_class, \
         patch('handlers.evidence_handler.config', mock_config):
        
        handler = EvidenceHandler()
        
        mock_db_class.assert_called_once_with(mock_config.POSTGRES_DSN)
        mock_broker_class.assert_called_once_with(mock_config.BUS_BROKER)
        mock_service_class.assert_called_once()
        assert handler.db is not None
        assert handler.broker is not None
        assert handler.service is not None
