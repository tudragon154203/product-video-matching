import pytest
from unittest.mock import AsyncMock, Mock, patch
from services.service import EvidenceBuilderService
from evidence import EvidenceGenerator


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_broker():
    return AsyncMock()


@pytest.fixture
def service(mock_db, mock_broker):
    return EvidenceBuilderService(mock_db, mock_broker, "./data")


def test_evidence_builder_initialization(service):
    """Test that the evidence builder service initializes correctly"""
    assert service is not None
    assert service.db is not None
    assert service.broker is not None
    assert service.evidence_generator is not None


@pytest.mark.asyncio
async def test_get_image_info(service):
    """Test getting image info"""
    # Mock the database response
    mock_result = {"local_path": "/path/to/image.jpg", "kp_blob_path": "/path/to/keypoints.blob"}
    service.db.fetch_one = AsyncMock(return_value=mock_result)
    
    # Call the method
    result = await service.get_image_info("test-img-id")
    
    # Verify the database call was made
    service.db.fetch_one.assert_called_once_with(
        "SELECT local_path, kp_blob_path FROM product_images WHERE img_id = $1",
        "test-img-id"
    )
    
    # Verify the result
    assert result == mock_result


@pytest.mark.asyncio
async def test_get_frame_info(service):
    """Test getting frame info"""
    # Mock the database response
    mock_result = {"local_path": "/path/to/frame.jpg", "kp_blob_path": "/path/to/keypoints.blob"}
    service.db.fetch_one = AsyncMock(return_value=mock_result)
    
    # Call the method
    result = await service.get_frame_info("test-frame-id")
    
    # Verify the database call was made
    service.db.fetch_one.assert_called_once_with(
        "SELECT local_path, kp_blob_path FROM video_frames WHERE frame_id = $1",
        "test-frame-id"
    )
    
    # Verify the result
    assert result == mock_result


@pytest.mark.asyncio
async def test_handle_match_result(service):
    """Test handling match result event"""
    # Mock event data
    event_data = {
        "job_id": "job123",
        "product_id": "product456",
        "video_id": "video789",
        "best_pair": {
            "img_id": "img123",
            "frame_id": "frame456",
            "score_pair": 0.95
        },
        "score": 0.92,
        "ts": 10.5
    }
    
    # Mock database responses
    service.db.fetch_one = AsyncMock(side_effect=[
        {"local_path": "/path/to/image.jpg", "kp_blob_path": "/path/to/keypoints1.blob"},
        {"local_path": "/path/to/frame.jpg", "kp_blob_path": "/path/to/keypoints2.blob"}
    ])
    
    # Mock evidence generator
    service.evidence_generator.create_evidence = Mock(return_value="/path/to/evidence.jpg")
    
    # Mock database execute
    service.db.execute = AsyncMock(return_value="UPDATE 1")
    
    # Mock broker publish
    service.broker.publish_event = AsyncMock()
    
    # Call the method
    await service.handle_match_result(event_data)
    
    # Verify database calls
    assert service.db.fetch_one.call_count == 2
    service.db.execute.assert_called_once()
    service.broker.publish_event.assert_called_once_with(
        "match.result.enriched",
        {
            **event_data,
            "evidence_path": "/path/to/evidence.jpg"
        },
        correlation_id="job123"
    )


@pytest.mark.asyncio
async def test_handle_match_result_missing_data(service):
    """Test handling match result event with missing data"""
    # Mock event data
    event_data = {
        "job_id": "job123",
        "product_id": "product456",
        "video_id": "video789",
        "best_pair": {
            "img_id": "img123",
            "frame_id": "frame456",
            "score_pair": 0.95
        },
        "score": 0.92,
        "ts": 10.5
    }
    
    # Mock database responses with missing data
    service.db.fetch_one = AsyncMock(return_value=None)
    
    # Mock logger
    with patch("services.service.logger") as mock_logger:
        # Call the method
        await service.handle_match_result(event_data)
        
        # Verify error was logged
        mock_logger.error.assert_called()