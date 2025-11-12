"""Integration test for handler messaging with correct method signatures"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from handlers.keypoint_handler import VisionKeypointHandler
from common_py.messaging_handler import MessageHandler


@pytest.mark.integration
class TestHandlerMessagingIntegration:
    """Integration test to verify handler methods work with messaging system"""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies"""
        with patch('handlers.keypoint_handler.DatabaseManager') as mock_db, \
                patch('handlers.keypoint_handler.MessageBroker') as mock_broker, \
                patch('handlers.keypoint_handler.VisionKeypointService') as mock_service:

            # Create mock instances
            db_instance = Mock()
            broker_instance = Mock()
            service_instance = Mock()

            mock_db.return_value = db_instance
            mock_broker.return_value = broker_instance
            mock_service.return_value = service_instance

            yield {
                'db': db_instance,
                'broker': broker_instance,
                'service': service_instance
            }

    @pytest.fixture
    def handler(self, mock_dependencies):
        """Create handler instance with mocked dependencies"""
        handler = VisionKeypointHandler()
        handler.db = mock_dependencies['db']
        handler.broker = mock_dependencies['broker']
        handler.service = mock_dependencies['service']
        return handler

    async def test_handler_signature_compatibility_with_messaging_system(self, handler):
        """Test that handler methods have correct signatures for messaging system"""

        # Test data that would come from RabbitMQ
        event_data = {
            "event_id": "test-event-123",
            "job_id": "test-job-456",
            "image_id": "test-image-789",
            "mask_path": "/test/path/mask.png"
        }
        correlation_id = "test-correlation-id-abc"

        # Mock incoming message
        mock_message = Mock()
        mock_message.correlation_id = correlation_id
        mock_message.body.decode.return_value = '{"test": "data"}'
        mock_message.ack = AsyncMock()
        mock_message.headers = None

        # Mock the handler methods to track calls
        handler.service.handle_products_image_masked = AsyncMock()

        # Test that the handler can be called with the exact signature the messaging system uses
        try:
            # This is exactly how MessageHandler calls the handler (line 42 in messaging_handler.py)
            await handler.handle_products_image_masked(event_data, correlation_id)
            signature_valid = True
        except TypeError as e:
            signature_valid = False
            pytest.fail(f"Handler method signature incompatible with messaging system: {e}")

        # Verify the signature is valid
        assert signature_valid, "Handler method should accept (event_data, correlation_id) parameters"

        # Verify the service was called correctly
        handler.service.handle_products_image_masked.assert_called_once_with(event_data)

    async def test_all_handler_methods_have_correct_signatures(self, handler):
        """Test that all handler methods accept the messaging system signature"""

        correlation_id = "test-correlation"

        # Mock all service methods
        handler.service.handle_products_image_masked = AsyncMock()
        handler.service.handle_video_keyframes_masked = AsyncMock()
        handler.service.handle_products_images_masked_batch = AsyncMock()
        handler.service.handle_videos_keyframes_masked_batch = AsyncMock()

        # Test each handler method with appropriate event data
        test_cases = [
            (handler.handle_products_image_masked, {
                "event_id": "test", "job_id": "test", "image_id": "test-img", "mask_path": "/test/path"
            }),
            (handler.handle_video_keyframes_masked, {
                "event_id": "test", "job_id": "test", "video_id": "test-vid", "ts": 1234567890,
                "frames": [{"frame_id": "frame1", "mask_path": "/test/path1", "ts": 1234567890}]
            }),
            (handler.handle_products_images_masked_batch, {
                "event_id": "test", "job_id": "test", "total_images": 5
            }),
            (handler.handle_videos_keyframes_masked_batch, {
                "event_id": "test", "job_id": "test", "total_keyframes": 10
            })
        ]

        for method, event_data in test_cases:
            try:
                await method(event_data, correlation_id)
            except TypeError as e:
                pytest.fail(f"Method {method.__name__} has incorrect signature: {e}")

        # Verify all methods were called successfully
        handler.service.handle_products_image_masked.assert_called_once()
        handler.service.handle_video_keyframes_masked.assert_called_once()
        batch_handler = handler.service.handle_products_images_masked_batch
        batch_handler.assert_called_once()
        keyframes_handler = handler.service.handle_videos_keyframes_masked_batch
        keyframes_handler.assert_called_once()

    async def test_message_handler_calls_with_correct_signature(self, mock_dependencies):
        """Test the full message handling flow with correct signatures"""

        # Setup handler
        handler = VisionKeypointHandler()
        handler.db = mock_dependencies['db']
        handler.broker = mock_dependencies['broker']
        handler.service = mock_dependencies['service']

        # Mock service method
        handler.service.handle_products_image_masked = AsyncMock()

        # Create message handler
        mock_exchange = Mock()
        mock_dlq_name = "test.dlq"
        msg_handler = MessageHandler(mock_exchange, mock_dlq_name)

        # Create mock message
        import json
        event_data = {
            "event_id": "test-event-123",
            "job_id": "test-job-456",
            "image_id": "test-image-789",
            "mask_path": "/test/path/mask.png"
        }

        mock_message = Mock()
        mock_message.correlation_id = "test-correlation-id"
        mock_message.body.decode.return_value = json.dumps(event_data)
        mock_message.ack = AsyncMock()
        mock_message.headers = None

        # Test the full flow - this should not raise a signature error
        try:
            await msg_handler.handle_message(
                mock_message,
                handler.handle_products_image_masked,
                "products.image.masked"
            )
            flow_successful = True
        except Exception as e:
            flow_successful = False
            pytest.fail(f"Message handling flow failed: {e}")

        assert flow_successful, "Message handling should work with correct signatures"

        # Verify the service method was called
        handler.service.handle_products_image_masked.assert_called_once_with(event_data)

        # Verify message was acknowledged
        mock_message.ack.assert_called_once()
