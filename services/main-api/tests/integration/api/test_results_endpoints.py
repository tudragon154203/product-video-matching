"""
Unit tests for results endpoints.
Minimal test cases focusing on core functionality.
"""
from models.results_schemas import MatchListResponse, MatchDetailResponse, StatsResponse, MatchResponse
from api.results_endpoints import router, get_results_service
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
import pytest
pytestmark = pytest.mark.integration


@pytest.fixture
def mock_results_service():
    """Mock results service"""
    service = MagicMock()
    service.get_results = AsyncMock()
    service.get_match = AsyncMock()
    service.get_stats = AsyncMock()
    service.get_evidence_path = AsyncMock()
    return service


@pytest.fixture
def test_app(mock_results_service):
    """Create test FastAPI app with mocked dependencies"""
    app = FastAPI()
    app.include_router(router)

    # Override dependency
    app.dependency_overrides[get_results_service] = lambda: mock_results_service

    return app


@pytest.fixture
def client(test_app):
    """Create test client"""
    return TestClient(test_app)


def test_get_results_success(client, mock_results_service):
    """Test successful results endpoint"""
    # Setup mock response
    mock_match = MatchResponse(
        match_id="match1",
        job_id="job1",
        product_id="prod1",
        video_id="vid1",
        score=0.85,
        created_at="2024-01-01T00:00:00",
        product_title="Test Product",
        video_title="Test Video",
        video_platform="youtube"
    )

    mock_response = MatchListResponse(
        items=[mock_match],
        total=1,
        limit=100,
        offset=0
    )

    mock_results_service.get_results.return_value = mock_response

    # Execute
    response = client.get("/results")

    # Verify
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["match_id"] == "match1"


def test_get_results_with_filters(client, mock_results_service):
    """Test results endpoint with filters"""
    mock_response = MatchListResponse(items=[], total=0, limit=50, offset=10)
    mock_results_service.get_results.return_value = mock_response

    # Execute
    response = client.get(
        "/results?industry=electronics&min_score=0.8&limit=50&offset=10")

    # Verify
    assert response.status_code == 200
    mock_results_service.get_results.assert_called_once_with(
        industry="electronics",
        min_score=0.8,
        job_id=None,
        limit=50,
        offset=10
    )


def test_get_match_success(client, mock_results_service):
    """Test successful match detail endpoint"""
    # Setup mock response
    from models.results_schemas import ProductResponse, VideoResponse

    mock_response = MatchDetailResponse(
        match_id="match1",
        job_id="job1",
        score=0.85,
        created_at="2024-01-01T00:00:00",
        product=ProductResponse(
            product_id="prod1",
            title="Test Product",
            created_at="2024-01-01T00:00:00",
            image_count=5
        ),
        video=VideoResponse(
            video_id="vid1",
            title="Test Video",
            platform="youtube",
            created_at="2024-01-01T00:00:00",
            frame_count=100
        )
    )

    mock_results_service.get_match.return_value = mock_response

    # Execute
    response = client.get("/matches/match1")

    # Verify
    assert response.status_code == 200
    data = response.json()
    assert data["match_id"] == "match1"
    assert data["product"]["product_id"] == "prod1"
    assert data["video"]["video_id"] == "vid1"


def test_get_match_not_found(client, mock_results_service):
    """Test match not found"""
    mock_results_service.get_match.return_value = None

    # Execute
    response = client.get("/matches/nonexistent")

    # Verify
    assert response.status_code == 404


def test_get_stats_success(client, mock_results_service):
    """Test successful stats endpoint"""
    mock_response = StatsResponse(
        products=100,
        product_images=500,
        videos=50,
        video_frames=1000,
        matches=200,
        jobs=10
    )

    mock_results_service.get_stats.return_value = mock_response

    # Execute
    response = client.get("/stats")

    # Verify
    assert response.status_code == 200
    data = response.json()
    assert data["products"] == 100
    assert data["matches"] == 200
