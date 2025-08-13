import pytest
from unittest.mock import AsyncMock, Mock
from service import VisionEmbeddingService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_broker():
    return AsyncMock()


@pytest.fixture
def service(mock_db, mock_broker):
    return VisionEmbeddingService(mock_db, mock_broker, "clip-vit-b32")


def test_vision_embedding_service_initialization(service):
    """Test that the vision embedding service initializes correctly"""
    assert service is not None
    assert service.db is not None
    assert service.broker is not None
    assert service.image_crud is not None
    assert service.frame_crud is not None
    assert service.extractor is not None