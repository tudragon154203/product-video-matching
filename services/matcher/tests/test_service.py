import pytest
from unittest.mock import AsyncMock, Mock
from service import MatcherService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_broker():
    return AsyncMock()


@pytest.fixture
def service(mock_db, mock_broker):
    return MatcherService(mock_db, mock_broker, "./data")


def test_matcher_service_initialization(service):
    """Test that the matcher service initializes correctly"""
    assert service is not None
    assert service.db is not None
    assert service.broker is not None
    assert service.match_crud is not None
    assert service.matching_engine is not None


@pytest.mark.asyncio
async def test_get_job_products(service):
    """Test getting job products"""
    # Mock the database response
    mock_result = [
        {"product_id": "prod-1", "title": "Product 1"},
        {"product_id": "prod-2", "title": "Product 2"}
    ]
    service.db.fetch_all = AsyncMock(return_value=mock_result)
    
    # Call the method
    result = await service.get_job_products("test-job-id")
    
    # Verify the database call was made
    service.db.fetch_all.assert_called_once_with(
        """
        SELECT DISTINCT p.product_id, p.title
        FROM products p
        WHERE p.job_id = $1
        """,
        "test-job-id"
    )
    
    # Verify the result
    assert result == mock_result


@pytest.mark.asyncio
async def test_get_job_videos(service):
    """Test getting job videos"""
    # Mock the database response
    mock_result = [
        {"video_id": "vid-1", "title": "Video 1"},
        {"video_id": "vid-2", "title": "Video 2"}
    ]
    service.db.fetch_all = AsyncMock(return_value=mock_result)
    
    # Call the method
    result = await service.get_job_videos("test-job-id")
    
    # Verify the database call was made
    service.db.fetch_all.assert_called_once_with(
        """
        SELECT DISTINCT v.video_id, v.title
        FROM videos v
        WHERE v.job_id = $1
        """,
        "test-job-id"
    )
    
    # Verify the result
    assert result == mock_result