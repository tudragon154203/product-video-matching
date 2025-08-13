import pytest
from unittest.mock import AsyncMock, Mock
from service import VectorIndexService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_broker():
    return AsyncMock()


@pytest.fixture
def service(mock_db, mock_broker):
    return VectorIndexService(mock_db, mock_broker)


def test_vector_index_service_initialization(service):
    """Test that the vector index service initializes correctly"""
    assert service is not None
    assert service.db is not None
    assert service.broker is not None
    assert service.vector_ops is not None