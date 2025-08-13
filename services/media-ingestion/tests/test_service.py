import pytest
from unittest.mock import AsyncMock, Mock
from service import MediaIngestionService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_broker():
    return AsyncMock()


@pytest.fixture
def service(mock_db, mock_broker):
    return MediaIngestionService(mock_db, mock_broker, "./data")


def test_media_ingestion_service_initialization(service):
    """Test that the media ingestion service initializes correctly"""
    assert service is not None
    assert service.db is not None
    assert service.broker is not None
    assert service.video_crud is not None
    assert service.frame_crud is not None
    assert service.ingestion is not None