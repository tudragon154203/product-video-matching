import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from aio_pika import IncomingMessage

# Import components from the service
from handlers.match_request_handler import handle_match_request
from services.data_models import MatchResult

# Mock Data
MOCK_INPUT_BODY = {
    "product": {"product_id": "P123", "image_url": "http://prod.img/poor_quality", "metadata": {}},
    "frame": {"frame_id": "F456", "video_id": "V789", "timestamp": 10.0, "image_url": "http://frame.img"}
}

# Match result with lower confidence/score due to poor quality
MOCK_LOW_CONFIDENCE_MATCH = MatchResult(
    product_id="P123",
    frame_id="F456",
    match_score=0.45, # Below the high threshold, but still a match
    bounding_box=[10.0, 20.0, 100.0, 200.0],
    confidence_level=0.55
)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_poor_quality_product_image_edge_case():
    """
    Tests the integration flow when a poor quality image is used.
    The handler should still process the request, and the result should reflect a lower confidence.
    """
    # Mock the incoming message
    mock_incoming_message = MagicMock(spec=IncomingMessage)
    mock_incoming_message.body = json.dumps(MOCK_INPUT_BODY).encode()
    mock_incoming_message.ack = AsyncMock()
    mock_incoming_message.reject = AsyncMock()

    # Mock the core matcher service to return a low confidence match
    with patch('handlers.match_request_handler.matcher_service.match', new_callable=AsyncMock) as mock_match:
        mock_match.return_value = [MOCK_LOW_CONFIDENCE_MATCH]

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

            # Assert 4: Published payload is correct
            expected_payload = {
                "product_id": "P123",
                "frame_id": "F456",
                "matches": [MOCK_LOW_CONFIDENCE_MATCH.model_dump()]
            }

            mock_publish.assert_called_once_with(json.dumps(expected_payload).encode())
