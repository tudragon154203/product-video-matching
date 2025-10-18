from unittest.mock import Mock, AsyncMock, patch
import pytest
from handlers.keypoint_handler import VisionKeypointHandler


class TestVisionKeypointHandler:
    """Unit tests for VisionKeypointHandler class"""

    def setup_method(self):
        """Setup for each test"""
        # Mock the dependencies
        with patch('handlers.keypoint_handler.DatabaseManager') as mock_db, \
                patch('handlers.keypoint_handler.MessageBroker') as mock_broker, \
                patch('handlers.keypoint_handler.VisionKeypointService') as mock_service:

            # Create mock instances
            self.mock_db = Mock()
            self.mock_broker = Mock()
            self.mock_service = Mock()

            mock_db.return_value = self.mock_db
            mock_broker.return_value = self.mock_broker
            mock_service.return_value = self.mock_service

            # Create the handler instance
            self.handler = VisionKeypointHandler()
            # Update it with our mocks
            self.handler.db = self.mock_db
            self.handler.broker = self.mock_broker
            self.handler.service = self.mock_service

    @pytest.mark.unit
    async def test_initialize(self):
        """Test the initialize method"""
        # Call initialize twice to test idempotency
        await self.handler.initialize()
        await self.handler.initialize()

        # Verify that the initialization flag is set
        assert self.handler.initialized is True

    @pytest.mark.unit
    async def test_handle_products_image_masked(self):
        """Test handling of products image masked event"""
        # Setup test data
        event_data = {
            "job_id": "job_123",
            "image_id": "img_456",
            "mask_path": "/path/to/mask.png",
            "event_id": "event_123"
        }

        # Mock the service method
        self.mock_service.handle_products_image_masked = AsyncMock()

        # Call the handler method
        correlation_id = "test-correlation-id"
        await self.handler.handle_products_image_masked(event_data, correlation_id)

        # Verify the service method was called
        self.mock_service.handle_products_image_masked.assert_called_once_with(event_data)

    @pytest.mark.unit
    async def test_handle_video_keyframes_masked(self):
        """Test handling of video keyframes masked event"""
        # Setup test data
        event_data = {
            "job_id": "job_789",
            "video_id": "video_789",
            "event_id": "event_789",
            "ts": 1672531200,  # Unix timestamp for 2023-01-01T00:00:00Z
            "frames": [{"frame_id": "frame_001", "mask_path": "/path/to/mask1.png", "ts": 1672531200}]
        }

        # Mock the service method
        self.mock_service.handle_video_keyframes_masked = AsyncMock()

        # Call the handler method
        correlation_id = "test-correlation-id"
        await self.handler.handle_video_keyframes_masked(event_data, correlation_id)

        # Verify the service method was called
        self.mock_service.handle_video_keyframes_masked.assert_called_once_with(event_data)

    @pytest.mark.unit
    async def test_handle_products_images_masked_batch(self):
        """Test handling of products images masked batch event"""
        # Setup test data
        event_data = {"job_id": "job_abc", "total_images": 10, "event_id": "event_abc"}

        # Mock the service method
        self.mock_service.handle_products_images_masked_batch = AsyncMock()

        # Call the handler method
        correlation_id = "test-correlation-id"
        await self.handler.handle_products_images_masked_batch(event_data, correlation_id)

        # Verify the service method was called
        self.mock_service.handle_products_images_masked_batch.assert_called_once_with(event_data)

    @pytest.mark.unit
    async def test_handle_videos_keyframes_masked_batch(self):
        """Test handling of videos keyframes masked batch event"""
        # Setup test data
        event_data = {"job_id": "job_def", "event_id": "event_123", "total_keyframes": 5}

        # Mock the service method
        self.mock_service.handle_videos_keyframes_masked_batch = AsyncMock()

        # Call the handler method
        correlation_id = "test-correlation-id"
        await self.handler.handle_videos_keyframes_masked_batch(event_data, correlation_id)

        # Verify the service method was called
        self.mock_service.handle_videos_keyframes_masked_batch.assert_called_once_with(event_data)
