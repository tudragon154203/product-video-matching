import pytest
from unittest.mock import AsyncMock, Mock
from service import EvidenceBuilderService


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