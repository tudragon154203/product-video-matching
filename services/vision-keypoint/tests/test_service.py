import pytest
from unittest.mock import AsyncMock, Mock
from service import VisionKeypointService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_broker():
    return AsyncMock()


@pytest.fixture
def service(mock_db, mock_broker):
    return VisionKeypointService(mock_db, mock_broker, "./data")


def test_vision_keypoint_service_initialization(service):
    """Test that the vision keypoint service initializes correctly"""
    assert service is not None
    assert service.db is not None
    assert service.broker is not None
    assert service.extractor is not None