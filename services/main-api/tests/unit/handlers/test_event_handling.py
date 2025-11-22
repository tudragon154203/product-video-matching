# Import the logger
from services.phase.phase_event_service import logger as phase_event_service_logger
from handlers.broker_handler import BrokerHandler
from handlers.database_handler import DatabaseHandler
from services.phase.phase_event_service import PhaseEventService
import os
import sys
import uuid
from unittest.mock import AsyncMock, Mock, patch
import pytest
pytestmark = pytest.mark.unit

# Add project root to PYTHONPATH for local imports
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))


class TestEventHandling:
    """Test the new event-driven architecture for job-based completion events"""

    @pytest.fixture
    def mock_db_handler(self):
        """Create a mock database handler with state tracking"""
        handler = Mock(spec=DatabaseHandler)
        # Track stored events: {job_id: set(event_types)}
        handler.stored_events = {}

        # Directly mock the async methods
        handler.store_phase_event = AsyncMock()
        handler.has_phase_event = AsyncMock()

        # Custom side effects for tracking state (synchronous functions)
        def store_side_effect(event_id, job_id, event_name):
            if job_id not in handler.stored_events:
                handler.stored_events[job_id] = set()
            handler.stored_events[job_id].add(event_name)
        handler.store_phase_event.side_effect = store_side_effect

        def has_side_effect(job_id, event_name):
            return job_id in handler.stored_events and event_name in handler.stored_events[job_id]
        handler.has_phase_event.side_effect = has_side_effect

        handler.get_job_phase = AsyncMock(return_value="feature_extraction")
        handler.update_job_phase = AsyncMock()
        handler.get_job_industry = AsyncMock(return_value="office_products")
        handler.get_job_asset_types = AsyncMock(
            return_value={"images": True, "videos": True})
        return handler

    @pytest.fixture
    def mock_broker_handler(self):
        """Create a mock broker handler"""
        handler = Mock(spec=BrokerHandler)
        handler.publish_match_request = AsyncMock()
        handler.publish_job_completed = AsyncMock()
        return handler

    @pytest.fixture
    def phase_event_service(self, mock_db_handler, mock_broker_handler):
        """Create a PhaseEventService instance with mocked dependencies"""
        return PhaseEventService(mock_db_handler, mock_broker_handler)

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
        mock_db_handler.store_phase_event.assert_called_once_with(
            event_id, job_id, "image.embeddings.completed")

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
        mock_db_handler.store_phase_event.assert_called_once_with(
            event_id, job_id, "video.embeddings.completed")

    @pytest.mark.asyncio
    async def test_handle_image_keypoints_completed_event(self, phase_event_service, mock_db_handler, mock_broker_handler):
        """Test handling of image.keypoints.completed event"""
        event_id = str(uuid.uuid4())
        job_id = "test-job-123"
        event_data = {
            "job_id": job_id,
            "event_id": event_id,
            "total_assets": 100,  # Added for validation
            "processed_assets": 100,
            "failed_assets": 0,
            "has_partial_completion": False,
            "watermark_ttl": 3600
        }

        # Mock database responses
        mock_db_handler.has_phase_event.return_value = False
        mock_db_handler.get_job_phase.return_value = "feature_extraction"

        await phase_event_service.handle_phase_event("image.keypoints.completed", event_data)

        # Verify the event was stored
        mock_db_handler.store_phase_event.assert_called_once_with(
            event_id, job_id, "image.keypoints.completed")

    @pytest.mark.asyncio
    async def test_zero_assets_handling(self, phase_event_service, mock_db_handler, mock_broker_handler, caplog):
        """Test handling of zero assets in job"""
        with patch.object(phase_event_service_logger, 'debug') as mock_logger_info:
            event_id = str(uuid.uuid4())
            job_id = "zero-assets-job"
            event_data = {
                "job_id": job_id,
                "event_id": event_id,
                "total_assets": 0,
                "processed_assets": 0,
                "failed_assets": 0,
                "has_partial_completion": False,
                "watermark_ttl": 3600
            }

            await phase_event_service.handle_phase_event("image.embeddings.completed", event_data)

            # Verify the event was stored
            mock_db_handler.store_phase_event.assert_called_once_with(
                event_id, job_id, "image.embeddings.completed")

            # Verify event was stored normally
            mock_logger_info.assert_any_call(
                f"Stored phase event: image.embeddings.completed for job {job_id}")

    @pytest.mark.asyncio
    async def test_timeout_partial_completion(self, phase_event_service, mock_db_handler, mock_broker_handler, caplog):
        """Test partial completion due to timeouts"""
        with patch.object(phase_event_service_logger, 'warning') as mock_logger_warning:
            event_id = str(uuid.uuid4())
            job_id = "timeout-job"
            event_data = {
                "job_id": job_id,
                "event_id": event_id,
                "total_assets": 100,
                "processed_assets": 70,
                "failed_assets": 0,
                "has_partial_completion": True,
                "watermark_ttl": 0  # Indicates timeout
            }

            await phase_event_service.handle_phase_event("video.embeddings.completed", event_data)

            # Verify partial completion is logged with the correct job_id and event_type
            mock_logger_warning.assert_called_once_with(
                f"Job completed with partial results for job {job_id} (video.embeddings.completed)")

    @pytest.mark.asyncio
    async def test_images_only_job(self, phase_event_service, mock_db_handler, mock_broker_handler):
        """Test job with only image assets"""
        job_id = "images-only-job"

        # Configure mock to return images-only job
        mock_db_handler.get_job_asset_types.return_value = {
            "images": True, "videos": False}

        # Only need to complete image-related events
        image_embeddings_event = {
            "job_id": job_id,
            "event_id": str(uuid.uuid4()),
            "total_assets": 50,
            "processed_assets": 50,
            "failed_assets": 0,
            "has_partial_completion": False,
            "watermark_ttl": 3600
        }
        image_keypoints_event = {
            "job_id": job_id,
            "event_id": str(uuid.uuid4()),
            "total_assets": 50,  # Added for validation
            "processed_assets": 50,
            "failed_assets": 0,
            "has_partial_completion": False,
            "watermark_ttl": 3600
        }

        # Process events
        await phase_event_service.handle_phase_event("image.embeddings.completed", image_embeddings_event)
        await phase_event_service.handle_phase_event("image.keypoints.completed", image_keypoints_event)

        # Should transition to matching phase
        mock_db_handler.update_job_phase.assert_called_with(job_id, "matching")

    @pytest.mark.asyncio
    async def test_videos_only_job(self, phase_event_service, mock_db_handler, mock_broker_handler):
        """Test job with only video assets"""
        job_id = "videos-only-job"

        # Configure mock to return videos-only job
        mock_db_handler.get_job_asset_types.return_value = {
            "images": False, "videos": True}

        # Only need to complete video-related events
        video_embeddings_event = {
            "job_id": job_id,
            "event_id": str(uuid.uuid4()),
            "total_assets": 20,
            "processed_assets": 20,
            "failed_assets": 0,
            "has_partial_completion": False,
            "watermark_ttl": 3600
        }
        video_keypoints_event = {
            "job_id": job_id,
            "event_id": str(uuid.uuid4()),
            "total_assets": 20,  # Added for validation
            "processed_assets": 20,
            "failed_assets": 0,
            "has_partial_completion": False,
            "watermark_ttl": 3600
        }

        # Process events
        await phase_event_service.handle_phase_event("video.embeddings.completed", video_embeddings_event)
        await phase_event_service.handle_phase_event("video.keypoints.completed", video_keypoints_event)

        # Should transition to matching phase
        mock_db_handler.update_job_phase.assert_called_with(job_id, "matching")

    @pytest.mark.asyncio
    async def test_end_to_end_event_flow(self, phase_event_service, mock_db_handler, mock_broker_handler):
        """Test complete event flow from collection to job completion"""
        job_id = "e2e-job"

        # Configure mock to return images and videos asset types
        mock_db_handler.get_job_asset_types.return_value = {
            "images": True, "videos": True}

        # Track stored events for phase transition checking
        stored_events = set()

        def has_phase_event_side_effect(job_id, event_name):
            # Always return True for collection completion events
            if event_name in ["products.collections.completed", "videos.collections.completed"]:
                return True
            # For other events, check if they've been stored
            return event_name in stored_events

        def store_phase_event_side_effect(event_id, job_id, event_name):
            stored_events.add(event_name)

        mock_db_handler.has_phase_event.side_effect = has_phase_event_side_effect
        mock_db_handler.store_phase_event.side_effect = store_phase_event_side_effect

        # Track current phase for proper mocking
        current_phase = "collection"

        def get_job_phase_side_effect(job_id):
            return current_phase

        def update_job_phase_side_effect(job_id, new_phase):
            nonlocal current_phase
            current_phase = new_phase

        mock_db_handler.get_job_phase.side_effect = get_job_phase_side_effect
        mock_db_handler.update_job_phase.side_effect = update_job_phase_side_effect

        # Simulate events in sequence
        events = [
            ("image.embeddings.completed", {
                "job_id": job_id,
                "event_id": str(uuid.uuid4()),
                "total_assets": 50,
                "processed_assets": 50,
                "failed_assets": 0,
                "has_partial_completion": False,
                "watermark_ttl": 3600
            }),
            ("video.embeddings.completed", {
                "job_id": job_id,
                "event_id": str(uuid.uuid4()),
                "total_assets": 20,
                "processed_assets": 20,
                "failed_assets": 0,
                "has_partial_completion": False,
                "watermark_ttl": 3600
            }),
            ("image.keypoints.completed", {
                "job_id": job_id,
                "event_id": str(uuid.uuid4()),
                "total_assets": 50,  # Added for validation
                "processed_assets": 50,
                "failed_assets": 0,
                "has_partial_completion": False,
                "watermark_ttl": 3600
            }),
            ("video.keypoints.completed", {
                "job_id": job_id,
                "event_id": str(uuid.uuid4()),
                "total_assets": 20,  # Added for validation
                "processed_assets": 20,
                "failed_assets": 0,
                "has_partial_completion": False,
                "watermark_ttl": 3600
            }),
            ("match.request.completed", {
                "job_id": job_id,
                "event_id": str(uuid.uuid4()),
                "total_assets": 1,  # Added for validation
                "processed_assets": 1,
                "failed_assets": 0,
                "has_partial_completion": False,
                "watermark_ttl": 3600
            }),
            ("evidences.generation.completed", {
                "job_id": job_id,
                "event_id": str(uuid.uuid4()),
                "total_assets": 1,  # Added for validation
                "processed_assets": 1,
                "failed_assets": 0,
                "has_partial_completion": False,
                "watermark_ttl": 3600
            })
        ]

        # Process all events
        for event_type, event_data in events:
            await phase_event_service.handle_phase_event(event_type, event_data)

        # Verify phase transitions
        phase_calls = mock_db_handler.update_job_phase.call_args_list

        # We expect transitions: collection -> feature_extraction -> matching -> evidence -> completed
        assert any(call[0] == (job_id, "feature_extraction")
                   for call in phase_calls)
        assert any(call[0] == (job_id, "matching") for call in phase_calls)
        assert any(call[0] == (job_id, "evidence") for call in phase_calls)
        assert any(call[0] == (job_id, "completed") for call in phase_calls)

        # Verify job completion event was published
        mock_broker_handler.publish_job_completed.assert_called_once_with(
            job_id)

    @pytest.mark.asyncio
    async def test_duplicate_event_handling(self, phase_event_service, mock_db_handler, mock_broker_handler, caplog):
        """Test idempotency with duplicate events"""
        with patch.object(phase_event_service_logger, 'debug') as mock_logger_info:
            event_id = str(uuid.uuid4())
            job_id = "duplicate-test-job"
            event_data = {
                "job_id": job_id,
                "event_id": event_id,
                "total_assets": 100,
                "processed_assets": 100,
                "failed_assets": 0,
                "has_partial_completion": False,
                "watermark_ttl": 3600
            }

            # First processing
            await phase_event_service.handle_phase_event("image.embeddings.completed", event_data)

            # Second processing with same event ID
            await phase_event_service.handle_phase_event("image.embeddings.completed", event_data)

            # Verify event stored only once and duplicate is skipped
            assert mock_db_handler.store_phase_event.call_count == 1
            mock_logger_info.assert_any_call(
                f"Duplicate event, skipping: {event_id} for job {job_id}")

    @pytest.mark.asyncio
    async def test_handle_video_keypoints_completed_event(self, phase_event_service, mock_db_handler, mock_broker_handler):
        """Test handling of video.keypoints.completed event"""
        event_id = str(uuid.uuid4())
        job_id = "test-job-123"
        event_data = {
            "job_id": job_id,
            "event_id": event_id,
            "total_assets": 100,  # Added for validation
            "processed_assets": 100,
            "failed_assets": 0,
            "has_partial_completion": False,
            "watermark_ttl": 3600
        }

        # Mock database responses
        mock_db_handler.has_phase_event.return_value = False
        mock_db_handler.get_job_phase.return_value = "feature_extraction"

        await phase_event_service.handle_phase_event("video.keypoints.completed", event_data)

        # Verify the event was stored
        mock_db_handler.store_phase_event.assert_called_once_with(
            event_id, job_id, "video.keypoints.completed")

    @pytest.mark.asyncio
    async def test_duplicate_event_id_handling(self, phase_event_service, mock_db_handler, mock_broker_handler):
        """Test that duplicate event IDs are handled correctly"""
        event_id = str(uuid.uuid4())
        job_id = "test-job-123"
        event_data = {
            "job_id": job_id,
            "event_id": event_id,
            "total_assets": 100,  # Added for validation
            "processed_assets": 100,
            "failed_assets": 0,
            "has_partial_completion": False,
            "watermark_ttl": 3600
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

        # The actual phase transition logic is tested in test_phase_transitions.py
        # Here we only test that handle_phase_event correctly calls check_phase_transitions
        await phase_event_service.handle_phase_event(
            "image.embeddings.completed",
            {
                "job_id": job_id,
                "event_id": str(uuid.uuid4()),
                "total_assets": 100,  # Added for validation
                "processed_assets": 100,
                "failed_assets": 0,
                "has_partial_completion": False,
                "watermark_ttl": 3600
            }
        )

    @pytest.mark.asyncio
    async def test_partial_completion_flag_handling(self, phase_event_service, mock_db_handler, mock_broker_handler, caplog):
        """Test handling of partial completion flag"""
        with patch.object(phase_event_service_logger, 'warning') as mock_logger_warning:
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
            mock_logger_warning.assert_called_once_with(
                f"Job completed with partial results for job {job_id} (image.embeddings.completed)")

    @pytest.mark.asyncio
    async def test_missing_event_id_handling(self, phase_event_service, mock_db_handler, mock_broker_handler, caplog):
        """Test handling of events with missing event_id or job_id"""
        with patch.object(phase_event_service_logger, 'error') as mock_logger_error:
            event_data = {
                "job_id": "test-job-123",
                "total_assets": 100,  # Added for validation
                "processed_assets": 100,
                "failed_assets": 0,
                "has_partial_completion": False,
                "watermark_ttl": 3600
                # Missing event_id
            }

            await phase_event_service.handle_phase_event("image.embeddings.completed", event_data)

            # Verify validation errors are logged
            mock_logger_error.assert_any_call(
                "Missing event_id or job_id in event: image.embeddings.completed")

            event_data = {
                "event_id": str(uuid.uuid4()),
                "total_assets": 100,  # Added for validation
                "processed_assets": 100,
                "failed_assets": 0,
                "has_partial_completion": False,
                "watermark_ttl": 3600
                # Missing job_id
            }

            await phase_event_service.handle_phase_event("image.embeddings.completed", event_data)

            # Verify validation errors are logged
            mock_logger_error.assert_any_call(
                "Missing event_id or job_id in event: image.embeddings.completed")
