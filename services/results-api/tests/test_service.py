import pytest
from unittest.mock import AsyncMock, Mock
from services.service import ResultsService
from common_py.models import Product, Video, Match

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

@pytest.mark.asyncio
async def test_get_results(service, mock_db):
    """Test get_results method"""
    # Mock the CRUD methods
    mock_match = Mock()
    mock_match.match_id = "match1"
    mock_match.product_id = "prod1"
    mock_match.video_id = "vid1"
    mock_match.score = 0.95
    
    service.match_crud.list_matches = AsyncMock(return_value=[mock_match])
    
    mock_product = Mock()
    mock_product.title = "Test Product"
    service.product_crud.get_product = AsyncMock(return_value=mock_product)
    
    mock_video = Mock()
    mock_video.title = "Test Video"
    mock_video.platform = "youtube"
    service.video_crud.get_video = AsyncMock(return_value=mock_video)
    
    # Mock fetch_val for created_at.isoformat() calls
    mock_db.fetch_val = AsyncMock(return_value=0)
    
    results = await service.get_results(min_score=0.9, limit=10)
    
    assert len(results) == 1
    assert results[0]["match_id"] == "match1"
    assert results[0]["score"] == 0.95
    assert results[0]["product_title"] == "Test Product"
    assert results[0]["video_title"] == "Test Video"

@pytest.mark.asyncio
async def test_get_product(service):
    """Test get_product method"""
    # Mock the CRUD method
    mock_product = Mock()
    mock_product.product_id = "prod1"
    mock_product.src = "amazon"
    mock_product.asin_or_itemid = "ASIN123"
    mock_product.title = "Test Product"
    mock_product.brand = "Test Brand"
    mock_product.url = "https://example.com/product"
    mock_product.created_at = Mock()
    mock_product.created_at.isoformat.return_value = "2023-01-01T00:00:00"
    
    service.product_crud.get_product = AsyncMock(return_value=mock_product)
    
    # Mock fetch_val for image count
    service.db.fetch_val = AsyncMock(return_value=5)
    
    result = await service.get_product("prod1")
    
    assert result is not None
    assert result["product_id"] == "prod1"
    assert result["title"] == "Test Product"
    assert result["brand"] == "Test Brand"
    assert result["image_count"] == 5

@pytest.mark.asyncio
async def test_get_video(service):
    """Test get_video method"""
    # Mock the CRUD method
    mock_video = Mock()
    mock_video.video_id = "vid1"
    mock_video.platform = "youtube"
    mock_video.url = "https://youtube.com/watch?v=test"
    mock_video.title = "Test Video"
    mock_video.duration_s = 300
    mock_video.published_at = Mock()
    mock_video.published_at.isoformat.return_value = "2023-01-01T00:00:00"
    mock_video.created_at = Mock()
    mock_video.created_at.isoformat.return_value = "2023-01-01T00:00:00"
    
    service.video_crud.get_video = AsyncMock(return_value=mock_video)
    
    # Mock fetch_val for frame count
    service.db.fetch_val = AsyncMock(return_value=100)
    
    result = await service.get_video("vid1")
    
    assert result is not None
    assert result["video_id"] == "vid1"
    assert result["title"] == "Test Video"
    assert result["platform"] == "youtube"
    assert result["frame_count"] == 100

@pytest.mark.asyncio
async def test_get_match(service):
    """Test get_match method"""
    # Mock the CRUD methods
    mock_match = Mock()
    mock_match.match_id = "match1"
    mock_match.job_id = "job1"
    mock_match.product_id = "prod1"
    mock_match.video_id = "vid1"
    mock_match.best_img_id = "img1"
    mock_match.best_frame_id = "frame1"
    mock_match.score = 0.95
    mock_match.evidence_path = "/path/to/evidence.jpg"
    mock_match.created_at = Mock()
    mock_match.created_at.isoformat.return_value = "2023-01-01T00:00:00"
    
    service.match_crud.get_match = AsyncMock(return_value=mock_match)
    
    # Mock product and video
    mock_product = Mock()
    mock_product.product_id = "prod1"
    mock_product.src = "amazon"
    mock_product.asin_or_itemid = "ASIN123"
    mock_product.title = "Test Product"
    mock_product.brand = "Test Brand"
    mock_product.url = "https://example.com/product"
    mock_product.created_at = Mock()
    mock_product.created_at.isoformat.return_value = "2023-01-01T00:00:00"
    
    mock_video = Mock()
    mock_video.video_id = "vid1"
    mock_video.platform = "youtube"
    mock_video.url = "https://youtube.com/watch?v=test"
    mock_video.title = "Test Video"
    mock_video.duration_s = 300
    mock_video.published_at = Mock()
    mock_video.published_at.isoformat.return_value = "2023-01-01T00:00:00"
    mock_video.created_at = Mock()
    mock_video.created_at.isoformat.return_value = "2023-01-01T00:00:00"
    
    service.product_crud.get_product = AsyncMock(return_value=mock_product)
    service.video_crud.get_video = AsyncMock(return_value=mock_video)
    
    # Mock fetch_val for counts
    service.db.fetch_val = AsyncMock(side_effect=[5, 100])  # product_image_count, video_frame_count
    
    result = await service.get_match("match1")
    
    assert result is not None
    assert result["match_id"] == "match1"
    assert result["score"] == 0.95
    assert result["product"]["product_id"] == "prod1"
    assert result["video"]["video_id"] == "vid1"
    assert result["product"]["image_count"] == 5
    assert result["video"]["frame_count"] == 100

@pytest.mark.asyncio
async def test_get_evidence_path(service):
    """Test get_evidence_path method"""
    # Mock the CRUD method
    mock_match = Mock()
    mock_match.evidence_path = "/path/to/evidence.jpg"
    
    service.match_crud.get_match = AsyncMock(return_value=mock_match)
    
    # Mock os.path.exists to return True
    with pytest.MonkeyPatch().context() as m:
        m.setattr("services.service.os.path.exists", lambda path: True)
        
        result = await service.get_evidence_path("match1")
        
        assert result == "/path/to/evidence.jpg"

@pytest.mark.asyncio
async def test_get_stats(service):
    """Test get_stats method"""
    # Mock fetch_val to return counts
    service.db.fetch_val = AsyncMock(side_effect=[100, 200, 50, 300, 250, 10])
    
    result = await service.get_stats()
    
    assert result["products"] == 100
    assert result["product_images"] == 200
    assert result["videos"] == 50
    assert result["video_frames"] == 300
    assert result["matches"] == 250
    assert result["jobs"] == 10