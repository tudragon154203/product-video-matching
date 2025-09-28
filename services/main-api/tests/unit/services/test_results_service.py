"""
Unit tests for ResultsService.
Minimal test cases focusing on core functionality.
"""
from models.results_schemas import StatsResponse
from services.results.results_service import ResultsService
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import pytest
pytestmark = pytest.mark.unit


@pytest.fixture
def mock_db():
    """Mock database manager"""
    db = MagicMock()
    db.fetch_val = AsyncMock()
    return db


@pytest.fixture
def mock_crud():
    """Mock CRUD objects"""
    product_crud = MagicMock()
    video_crud = MagicMock()
    match_crud = MagicMock()

    # Setup async methods
    product_crud.get_product = AsyncMock()
    video_crud.get_video = AsyncMock()
    match_crud.get_match = AsyncMock()
    match_crud.list_matches = AsyncMock()
    match_crud.count_matches = AsyncMock()

    return product_crud, video_crud, match_crud


@pytest.fixture
def results_service(mock_db, mock_crud):
    """Create ResultsService with mocked dependencies"""
    service = ResultsService(mock_db)
    service.product_crud, service.video_crud, service.match_crud = mock_crud
    return service


@pytest.mark.asyncio
async def test_get_results_success(results_service, mock_crud):
    """Test successful results retrieval"""
    # Setup mock data
    mock_match = MagicMock()
    mock_match.match_id = "match1"
    mock_match.job_id = "job1"
    mock_match.product_id = "prod1"
    mock_match.video_id = "vid1"
    mock_match.score = 0.85
    mock_match.created_at = datetime.now()
    mock_match.best_img_id = "img1"
    mock_match.best_frame_id = "frame1"
    mock_match.ts = 10.5
    mock_match.evidence_path = "/path/to/evidence"

    mock_product = MagicMock()
    mock_product.title = "Test Product"

    mock_video = MagicMock()
    mock_video.title = "Test Video"
    mock_video.platform = "youtube"

    # Setup mock returns
    mock_crud[2].list_matches.return_value = [mock_match]  # match_crud
    mock_crud[2].count_matches.return_value = 1
    mock_crud[0].get_product.return_value = mock_product  # product_crud
    mock_crud[1].get_video.return_value = mock_video  # video_crud

    # Execute
    result = await results_service.get_results(limit=10, offset=0)

    # Verify
    assert len(result.items) == 1
    assert result.total == 1
    assert result.items[0].match_id == "match1"
    assert result.items[0].product_title == "Test Product"
    assert result.items[0].video_title == "Test Video"


@pytest.mark.asyncio
async def test_get_match_success(results_service, mock_crud, mock_db):
    """Test successful match detail retrieval"""
    # Setup mock data
    mock_match = MagicMock()
    mock_match.match_id = "match1"
    mock_match.job_id = "job1"
    mock_match.product_id = "prod1"
    mock_match.video_id = "vid1"
    mock_match.score = 0.85
    mock_match.created_at = datetime.now()
    mock_match.best_img_id = "img1"
    mock_match.best_frame_id = "frame1"
    mock_match.ts = 10.5
    mock_match.evidence_path = "/path/to/evidence"

    mock_product = MagicMock()
    mock_product.product_id = "prod1"
    mock_product.title = "Test Product"
    mock_product.created_at = datetime.now()
    mock_product.src = "amazon"
    mock_product.asin_or_itemid = "B123456"
    mock_product.brand = "TestBrand"
    mock_product.url = "http://example.com"

    mock_video = MagicMock()
    mock_video.video_id = "vid1"
    mock_video.title = "Test Video"
    mock_video.platform = "youtube"
    mock_video.url = "http://youtube.com/watch?v=123"
    mock_video.duration_s = 120
    mock_video.published_at = datetime.now()
    mock_video.created_at = datetime.now()

    # Setup mock returns
    mock_crud[2].get_match.return_value = mock_match  # match_crud
    mock_crud[0].get_product.return_value = mock_product  # product_crud
    mock_crud[1].get_video.return_value = mock_video  # video_crud
    mock_db.fetch_val.side_effect = [5, 100]  # image_count, frame_count

    # Execute
    result = await results_service.get_match("match1")

    # Verify
    assert result is not None
    assert result.match_id == "match1"
    assert result.product.product_id == "prod1"
    assert result.video.video_id == "vid1"


@pytest.mark.asyncio
async def test_get_stats_success(results_service, mock_db):
    """Test successful stats retrieval"""
    # Setup mock returns
    # products, images, videos, frames, matches, jobs
    mock_db.fetch_val.side_effect = [100, 500, 50, 1000, 200, 10]

    # Execute
    result = await results_service.get_stats()

    # Verify
    assert isinstance(result, StatsResponse)
    assert result.products == 100
    assert result.product_images == 500
    assert result.videos == 50
    assert result.video_frames == 1000
    assert result.matches == 200
    assert result.jobs == 10


@pytest.mark.asyncio
async def test_get_match_not_found(results_service, mock_crud):
    """Test match not found scenario"""
    # Setup mock returns
    mock_crud[2].get_match.return_value = None  # match_crud

    # Execute
    result = await results_service.get_match("nonexistent")

    # Verify
    assert result is None
