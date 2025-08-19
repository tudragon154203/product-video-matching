import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
import uuid
import sys
import os

# Add project root to PYTHONPATH for local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.phase.phase_event_service import PhaseEventService
from handlers.database_handler import DatabaseHandler
from handlers.broker_handler import BrokerHandler


class TestPhaseTransitionWithAssetTypes:
    """Test phase transitions with different asset types"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database"""
        return Mock()

    @pytest.fixture
    def db_handler(self, mock_db):
        """Create a DatabaseHandler instance with mocked database"""
        return DatabaseHandler(mock_db)

    @pytest.fixture
    def mock_broker_handler(self):
        """Create a mock broker handler"""
        handler = Mock(spec=BrokerHandler)
        handler.publish_match_request = AsyncMock()
        handler.publish_job_completed = AsyncMock()
        return handler

    @pytest.fixture
    def phase_event_service(self, db_handler, mock_broker_handler):
        """Create a PhaseEventService instance"""
        return PhaseEventService(db_handler, mock_broker_handler)

    @pytest.mark.asyncio
    async def test_phase_transition_images_only_job(self, phase_event_service, db_handler, mock_broker_handler):
        """Test phase transition for a job with only images"""
        job_id = "images-only-job"
        
        # Mock the database responses for an images-only job
        db_handler.get_job_counts = AsyncMock(return_value=(5, 0, 0))  # 5 products, 0 videos, 0 matches
        db_handler.get_features_counts = AsyncMock(return_value=(5, 0))  # 5 products with features, 0 videos with features
        db_handler.get_job_phase = AsyncMock(return_value="feature_extraction")
        db_handler.update_job_phase = AsyncMock()
        db_handler.get_job_industry = AsyncMock(return_value="office_products")
        
        # Mock that only image events have been received (no video events)
        def has_phase_event_side_effect(job_id, event_name):
            return event_name in ["image.embeddings.completed", "image.keypoints.completed"]
        
        db_handler.has_phase_event = AsyncMock(side_effect=has_phase_event_side_effect)

        # Trigger phase transition check
        await phase_event_service.check_phase_transitions(job_id, "image.keypoints.completed")

        # Verify phase was updated to matching (since only image events are required)
        db_handler.update_job_phase.assert_called_with(job_id, "matching")
        
        # Verify match request was published
        mock_broker_handler.publish_match_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_phase_transition_videos_only_job(self, phase_event_service, db_handler, mock_broker_handler):
        """Test phase transition for a job with only videos"""
        job_id = "videos-only-job"
        
        # Mock the database responses for a videos-only job
        db_handler.get_job_counts = AsyncMock(return_value=(0, 3, 0))  # 0 products, 3 videos, 0 matches
        db_handler.get_features_counts = AsyncMock(return_value=(0, 3))  # 0 products with features, 3 videos with features
        db_handler.get_job_phase = AsyncMock(return_value="feature_extraction")
        db_handler.update_job_phase = AsyncMock()
        db_handler.get_job_industry = AsyncMock(return_value="office_products")
        
        # Mock that only video events have been received (no image events)
        def has_phase_event_side_effect(job_id, event_name):
            return event_name in ["video.embeddings.completed", "video.keypoints.completed"]
        
        db_handler.has_phase_event = AsyncMock(side_effect=has_phase_event_side_effect)

        # Trigger phase transition check
        await phase_event_service.check_phase_transitions(job_id, "video.keypoints.completed")

        # Verify phase was updated to matching (since only video events are required)
        db_handler.update_job_phase.assert_called_with(job_id, "matching")
        
        # Verify match request was published
        mock_broker_handler.publish_match_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_phase_transition_images_and_videos_job(self, phase_event_service, db_handler, mock_broker_handler):
        """Test phase transition for a job with both images and videos"""
        job_id = "images-and-videos-job"
        
        # Mock the database responses for a job with both images and videos
        db_handler.get_job_counts = AsyncMock(return_value=(5, 3, 0))  # 5 products, 3 videos, 0 matches
        db_handler.get_features_counts = AsyncMock(return_value=(5, 3))  # 5 products with features, 3 videos with features
        db_handler.get_job_phase = AsyncMock(return_value="feature_extraction")
        db_handler.update_job_phase = AsyncMock()
        db_handler.get_job_industry = AsyncMock(return_value="office_products")
        
        # Mock that all events have been received
        def has_phase_event_side_effect(job_id, event_name):
            return event_name in [
                "image.embeddings.completed", 
                "video.embeddings.completed", 
                "image.keypoints.completed", 
                "video.keypoints.completed"
            ]
        
        db_handler.has_phase_event = AsyncMock(side_effect=has_phase_event_side_effect)

        # Trigger phase transition check
        await phase_event_service.check_phase_transitions(job_id, "video.keypoints.completed")

        # Verify phase was updated to matching (since all events are required)
        db_handler.update_job_phase.assert_called_with(job_id, "matching")
        
        # Verify match request was published
        mock_broker_handler.publish_match_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_phase_transition_incomplete_events(self, phase_event_service, db_handler, mock_broker_handler):
        """Test that phase transition doesn't happen when required events are missing"""
        job_id = "incomplete-job"
        
        # Mock the database responses for a job with both images and videos
        db_handler.get_job_counts = AsyncMock(return_value=(5, 3, 0))  # 5 products, 3 videos, 0 matches
        db_handler.get_features_counts = AsyncMock(return_value=(5, 3))  # 5 products with features, 3 videos with features
        db_handler.get_job_phase = AsyncMock(return_value="feature_extraction")
        db_handler.update_job_phase = AsyncMock()
        db_handler.get_job_industry = AsyncMock(return_value="office_products")
        
        # Mock that only some events have been received (missing video.keypoints.completed)
        def has_phase_event_side_effect(job_id, event_name):
            return event_name in [
                "image.embeddings.completed", 
                "video.embeddings.completed", 
                "image.keypoints.completed"
                # Missing: "video.keypoints.completed"
            ]
        
        db_handler.has_phase_event = AsyncMock(side_effect=has_phase_event_side_effect)

        # Trigger phase transition check
        await phase_event_service.check_phase_transitions(job_id, "image.keypoints.completed")

        # Verify phase was NOT updated to matching (since not all required events are received)
        db_handler.update_job_phase.assert_not_called()
        
        # Verify match request was NOT published
        mock_broker_handler.publish_match_request.assert_not_called()