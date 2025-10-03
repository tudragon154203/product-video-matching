import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from aio_pika import IncomingMessage

# Import components from the service
from handlers.match_request_handler import handle_match_request

# Mock Data
MOCK_INPUT_BODY = {
    "product": {"product_id": "P123", "image_url": "http://prod.img", "metadata": {}},
    "frame": {"frame_id": "F456", "video_id": "V789", "timestamp": 10.0, "image_url": "http://frame.img"}
}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_no_match_found_scenario():
    """
    Tests the integration flow when the matcher service finds no match.
    The handler should publish an empty list of matches and acknowledge the message.
    """
    # Mock the incoming message
    mock_incoming_message = MagicMock(spec=IncomingMessage)
    mock_incoming_message.body = json.dumps(MOCK_INPUT_BODY).encode()
    mock_incoming_message.ack = AsyncMock()
    mock_incoming_message.reject = AsyncMock()

    # Mock the core matcher service to return an empty list (no match)
    with patch('handlers.match_request_handler.matcher_service.match', new_callable=AsyncMock) as mock_match:
        mock_match.return_value = []

        # Mock the publisher instance
        with patch('handlers.match_request_handler.publisher') as mock_publisher_instance:
            mock_publisher_instance.publish = AsyncMock()
            mock_publish = mock_publisher_instance.publish

            # Act: Call the handler
            await handle_match_request(mock_incoming_message)

            # Assert 1: Core service was called correctly
            mock_match.assert_called_once()

            # Assert 2: Result was published
            mock_publish.assert_called_once()

            # Assert 3: Message was acknowledged
            mock_incoming_message.ack.assert_called_once()
            mock_incoming_message.reject.assert_not_called()

            # Assert 4: Published payload is correct (empty matches list)
            expected_payload = {
                "product_id": "P123",
                "frame_id": "F456",
                "matches": []
            }

            mock_publish.assert_called_once_with(json.dumps(expected_payload).encode())
