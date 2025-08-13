import pytest
from unittest.mock import AsyncMock, Mock
from service import ResultsService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def service(mock_db):
    return ResultsService(mock_db)


def test_results_service_initialization(service):
    """Test that the results service initializes correctly"""
    assert service is not None
    assert service.db is not None
    assert service.product_crud is not None
    assert service.video_crud is not None
    assert service.match_crud is not None