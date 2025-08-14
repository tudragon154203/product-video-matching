import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
import uuid
import sys
import os

# Add project root to PYTHONPATH for local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.phase_event_service import PhaseEventService
from services.phase_management_service import PhaseManagementService
from handlers.database_handler import DatabaseHandler
from handlers.broker_handler import BrokerHandler


class TestEventHandling:
    """Test the new event-driven architecture for job-based completion events"""

    @pytest.fixture
    def mock_db_handler(self):
        """Create a mock database handler"""
        handler = Mock(spec=DatabaseHandler)
        handler.store_phase_event = AsyncMock()
        handler.has_phase_event = AsyncMock(return_value=False)
        handler.get_job_phase = AsyncMock(return_value="feature_extraction")
        handler.update_job_phase = AsyncMock()
        handler.get_job_industry = AsyncMock(return_value="office_products")
        return handler

    @pytest.fixture
    def mock_broker_handler(self):
        """Create a mock broker handler"""
        handler = Mock(spec=BrokerHandler)
        handler.publish_match_request = AsyncMock()
        return handler

    @pytest.fixture
    def phase_event_service(self, mock_db_handler, mock_broker_handler):
        """Create a PhaseEventService instance with mocked dependencies"""
        return PhaseEventService(mock_db_handler, mock_broker_handler)

    @pytest.fixture
    def phase_management_service(self, mock_db_handler, mock_broker_handler):
        """Create a PhaseManagementService instance with mocked dependencies"""
        return PhaseManagementService(mock_db_handler, mock_broker_handler)

    @pytest.mark.asyncio
    async def test_handle_image_embeddings_completed_event(self, phase_event_service, mock_db_handler, mock_broker_handler):
        """Test handling of image.embeddings.completed event"""
        event_id = str(uuid.uuid4())
        job_id = "test-job-123"
        event_data = {
            "job_id": job_id,
            "event_id": event_id,
            "total_assets": 100,
            "processed_assets": 95,
            "failed_assets": 5,
            "has_partial_completion": True,
            "watermark_ttl": 3600
        }

        # Mock database responses
        mock_db_handler.has_phase_event.return_value = False
        mock_db_handler.get_job_phase.return_value = "feature_extraction"

        await phase_event_service.handle_phase_event("image.embeddings.completed", event_data)

        # Verify the event was stored
        mock_db_handler.store_phase_event.assert_called_once_with(event_id, job_id, "image.embeddings.completed")
        
        # Verify phase transition was checked
        mock_db_handler.get_job_phase.assert_called_with(job_id)

    @pytest.mark.asyncio
    async def test_handle_video_embeddings_completed_event(self, phase_event_service, mock_db_handler, mock_broker_handler):
        """Test handling of video.embeddings.completed event"""
        event_id = str(uuid.uuid4())
        job_id = "test-job-123"
        event_data = {
            "job_id": job_id,
            "event_id": event_id,
            "total_assets": 50,
            "processed_assets": 50,
            "failed_assets": 0,
            "has_partial_completion": False,
            "watermark_ttl": 3600
        }

        # Mock database responses
        mock_db_handler.has_phase_event.return_value = False
        mock_db_handler.get_job_phase.return_value = "feature_extraction"

        await phase_event_service.handle_phase_event("video.embeddings.completed", event_data)

        # Verify the event was stored
        mock_db_handler.store_phase_event.assert_called_once_with(event_id, job_id, "video.embeddings.completed")

    @pytest.mark.asyncio
    async def test_handle_image_keypoints_completed_event(self, phase_event_service, mock_db_handler, mock_broker_handler):
        """Test handling of image.keypoints.completed event"""
        event_id = str(uuid.uuid4())
        job_id = "test-job-123"
        event_data = {
            "job_id": job_id,
            "event_id": event_id
        }

        # Mock database responses
        mock_db_handler.has_phase_event.return_value = False
        mock_db_handler.get_job_phase.return_value = "feature_extraction"

        await phase_event_service.handle_phase_event("image.keypoints.completed", event_data)

        # Verify the event was stored
        mock_db_handler.store_phase_event.assert_called_once_with(event_id, job_id, "image.keypoints.completed")

    @pytest.mark.asyncio
    async def test_handle_video_keypoints_completed_event(self, phase_event_service, mock_db_handler, mock_broker_handler):
        """Test handling of video.keypoints.completed event"""
        event_id = str(uuid.uuid4())
        job_id = "test-job-123"
        event_data = {
            "job_id": job_id,
            "event_id": event_id
        }

        # Mock database responses
        mock_db_handler.has_phase_event.return_value = False
        mock_db_handler.get_job_phase.return_value = "feature_extraction"

        await phase_event_service.handle_phase_event("video.keypoints.completed", event_data)

        # Verify the event was stored
        mock_db_handler.store_phase_event.assert_called_once_with(event_id, job_id, "video.keypoints.completed")

    @pytest.mark.asyncio
    async def test_duplicate_event_id_handling(self, phase_event_service, mock_db_handler, mock_broker_handler):
        """Test that duplicate event IDs are handled correctly"""
        event_id = str(uuid.uuid4())
        job_id = "test-job-123"
        event_data = {
            "job_id": job_id,
            "event_id": event_id
        }

        # First call should succeed
        await phase_event_service.handle_phase_event("image.keypoints.completed", event_data)
        
        # Second call with same event ID should be ignored
        await phase_event_service.handle_phase_event("image.keypoints.completed", event_data)

        # Verify store_phase_event was called only once
        assert mock_db_handler.store_phase_event.call_count == 1

    @pytest.mark.asyncio
    async def test_phase_transition_to_matching(self, phase_event_service, mock_db_handler, mock_broker_handler):
        """Test phase transition from feature_extraction to matching when all four events are received"""
        job_id = "test-job-123"
        
        # Mock that all four events have been received
        mock_db_handler.has_phase_event.side_effect = lambda job_id, event_name: {
            "image.embeddings.completed": True,
            "video.embeddings.completed": True,
            "image.keypoints.completed": True,
            "video.keypoints.completed": True
        }.get(event_name, False)
        
        mock_db_handler.get_job_phase.return_value = "feature_extraction"

        # Trigger phase transition check
        await phase_event_service.check_phase_transitions(job_id, "image.embeddings.completed")

        # Verify phase was updated to matching
        mock_db_handler.update_job_phase.assert_called_with(job_id, "matching")
        
        # Verify match request was published
        mock_broker_handler.publish_match_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_partial_completion_flag_handling(self, phase_event_service, mock_db_handler, mock_broker_handler, caplog):
        """Test handling of partial completion flag"""
        event_id = str(uuid.uuid4())
        job_id = "test-job-123"
        event_data = {
            "job_id": job_id,
            "event_id": event_id,
            "total_assets": 100,
            "processed_assets": 80,
            "failed_assets": 20,
            "has_partial_completion": True,
            "watermark_ttl": 3600
        }

        await phase_event_service.handle_phase_event("image.embeddings.completed", event_data)

        # Verify that partial completion is logged
        assert "Job completed with partial results" in caplog.text
        assert job_id in caplog.text

    @pytest.mark.asyncio
    async def test_missing_event_id_handling(self, phase_event_service, mock_db_handler, mock_broker_handler, caplog):
        """Test handling of events with missing event_id or job_id"""
        event_data = {
            "job_id": "test-job-123"
            # Missing event_id
        }

        await phase_event_service.handle_phase_event("image.embeddings.completed", event_data)

        # Verify error is logged
        assert "Missing event_id or job_id in event" in caplog.text

        event_data = {
            "event_id": str(uuid.uuid4())
            # Missing job_id
        }

        await phase_event_service.handle_phase_event("image.embeddings.completed", event_data)

        # Verify error is logged
        assert "Missing event_id or job_id in event" in caplog.text

    def test_phase_management_service_deprecation(self, phase_management_service, caplog):
        """Test that phase management service logs deprecation message"""
        # Run the deprecated phase update task
        asyncio.run(phase_management_service.phase_update_task())
        
        # Verify deprecation message is logged
        assert "Phase update task is deprecated in Sprint 6" in caplog.text
        assert "Using event-driven phase transitions instead" in caplog.text


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])