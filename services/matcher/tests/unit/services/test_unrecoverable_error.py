from handlers.match_request_handler import handle_match_request
import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from aio_pika import IncomingMessage

pytestmark = pytest.mark.unit

# Import components from the service

# Mock Data
MOCK_INPUT_BODY = {
    "product": {"product_id": "P123", "image_url": "http://prod.img", "metadata": {}},
    "frame": {"frame_id": "F456", "video_id": "V789", "timestamp": 10.0, "image_url": "http://frame.img"}
}


@pytest.mark.asyncio
async def test_unrecoverable_error_during_matching_edge_case():
    """
    Unit test for handling unrecoverable error during matching.
    The handler should reject the message and not publish a result.
    """
    # Mock the incoming message
    mock_incoming_message = MagicMock(spec=IncomingMessage)
    mock_incoming_message.body = json.dumps(MOCK_INPUT_BODY).encode()
    mock_incoming_message.ack = AsyncMock()
    mock_incoming_message.reject = AsyncMock()

    # Mock the core matcher service to raise an exception
    with patch('handlers.match_request_handler.matcher_service.match', new_callable=AsyncMock) as mock_match:
        mock_match.side_effect = Exception("Simulated Unrecoverable Error")

        # Mock the publisher
        with patch('handlers.match_request_handler.publisher.publish', new_callable=AsyncMock) as mock_publish:

            # Act: Call the handler
            await handle_match_request(mock_incoming_message)

            # Assert 1: Core service was called
            mock_match.assert_called_once()

            # Assert 2: Result was NOT published
            mock_publish.assert_not_called()

            # Assert 3: Message was rejected (not acknowledged)
            mock_incoming_message.ack.assert_not_called()
            mock_incoming_message.reject.assert_called_once_with(requeue=False)
