"""
Unit tests for service layer components.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from services.results_service import ResultsService
from core.exceptions import DatabaseError, ServiceError
from tests.conftest import MockProduct, MockVideo, MockMatch


class TestResultsService:
    """Test ResultsService class"""
    
    @pytest.fixture
    def service(self, mock_database, mock_product_crud, mock_video_crud, mock_match_crud):
        """Create a ResultsService instance with mocked dependencies"""
        service = ResultsService(mock_database)
        service.product_crud = mock_product_crud
        service.video_crud = mock_video_crud
        service.match_crud = mock_match_crud
        return service
    
    @pytest.mark.asyncio
    async def test_get_results_success(self, service, mock_match_crud, mock_product_crud, mock_video_crud):
        """Test successful get_results operation"""
        # Setup mock data
        mock_match = MockMatch()
        mock_product = MockProduct()
        mock_video = MockVideo()
        
        mock_match_crud.list_matches.return_value = [mock_match]
        mock_product_crud.get_product.return_value = mock_product
        mock_video_crud.get_video.return_value = mock_video
        
        # Call the method
        results = await service.get_results(limit=10, offset=0)
        
        # Assertions
        assert len(results) == 1
        assert results[0]["match_id"] == "test-match-1"
        assert results[0]["product_title"] == "Test Product"
        assert results[0]["video_title"] == "Test Video"
        
        mock_match_crud.list_matches.assert_called_once_with(
            job_id=None, min_score=None, limit=10, offset=0
        )
    
    @pytest.mark.asyncio
    async def test_get_results_with_industry_filter(self, service, mock_match_crud, mock_product_crud, mock_video_crud):
        """Test get_results with industry filter"""
        # Setup mock data
        mock_match = MockMatch()
        mock_product = MockProduct(title="Electronics Product")
        mock_video = MockVideo()
        
        mock_match_crud.list_matches.return_value = [mock_match]
        mock_product_crud.get_product.return_value = mock_product
        mock_video_crud.get_video.return_value = mock_video
        
        # Call with industry filter that matches
        results = await service.get_results(industry="electronics")
        assert len(results) == 1
        
        # Call with industry filter that doesn't match
        results = await service.get_results(industry="clothing")
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_get_results_database_error(self, service, mock_match_crud):
        """Test get_results with database error"""
        mock_match_crud.list_matches.side_effect = Exception("Database connection failed")
        
        with pytest.raises(ServiceError) as exc_info:
            await service.get_results()
        
        assert "Failed to get results" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_product_success(self, service, mock_product_crud, mock_database):
        """Test successful get_product operation"""
        # Setup mock data
        mock_product = MockProduct()
        mock_product_crud.get_product.return_value = mock_product
        mock_database.fetch_val.return_value = 5  # image count
        
        # Call the method
        result = await service.get_product("test-product-1")
        
        # Assertions
        assert result is not None
        assert result["product_id"] == "test-product-1"
        assert result["title"] == "Test Product"
        assert result["image_count"] == 5
        
        mock_product_crud.get_product.assert_called_once_with("test-product-1")
    
    @pytest.mark.asyncio
    async def test_get_product_not_found(self, service, mock_product_crud):
        """Test get_product when product not found"""
        mock_product_crud.get_product.return_value = None
        
        result = await service.get_product("nonexistent-product")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_product_database_error(self, service, mock_product_crud):
        """Test get_product with database error"""
        mock_product_crud.get_product.side_effect = Exception("Database error")
        
        with pytest.raises(ServiceError) as exc_info:
            await service.get_product("test-product-1")
        
        assert "Failed to get product" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_video_success(self, service, mock_video_crud, mock_database):
        """Test successful get_video operation"""
        # Setup mock data
        mock_video = MockVideo()
        mock_video_crud.get_video.return_value = mock_video
        mock_database.fetch_val.return_value = 100  # frame count
        
        # Call the method
        result = await service.get_video("test-video-1")
        
        # Assertions
        assert result is not None
        assert result["video_id"] == "test-video-1"
        assert result["title"] == "Test Video"
        assert result["frame_count"] == 100
        
        mock_video_crud.get_video.assert_called_once_with("test-video-1")
    
    @pytest.mark.asyncio
    async def test_get_video_not_found(self, service, mock_video_crud):
        """Test get_video when video not found"""
        mock_video_crud.get_video.return_value = None
        
        result = await service.get_video("nonexistent-video")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_match_success(self, service, mock_match_crud, mock_product_crud, mock_video_crud, mock_database):
        """Test successful get_match operation"""
        # Setup mock data
        mock_match = MockMatch()
        mock_product = MockProduct()
        mock_video = MockVideo()
        
        mock_match_crud.get_match.return_value = mock_match
        mock_product_crud.get_product.return_value = mock_product
        mock_video_crud.get_video.return_value = mock_video
        mock_database.fetch_val.side_effect = [5, 100]  # image count, frame count
        
        # Call the method
        result = await service.get_match("test-match-1")
        
        # Assertions
        assert result is not None
        assert result["match_id"] == "test-match-1"
        assert "product" in result
        assert "video" in result
        assert result["product"]["product_id"] == "test-product-1"
        assert result["video"]["video_id"] == "test-video-1"
        
        mock_match_crud.get_match.assert_called_once_with("test-match-1")
    
    @pytest.mark.asyncio
    async def test_get_match_not_found(self, service, mock_match_crud):
        """Test get_match when match not found"""
        mock_match_crud.get_match.return_value = None
        
        result = await service.get_match("nonexistent-match")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_evidence_path_success(self, service, mock_match_crud):
        """Test successful get_evidence_path operation"""
        # Setup mock data
        mock_match = MockMatch(evidence_path="/path/to/evidence.jpg")
        mock_match_crud.get_match.return_value = mock_match
        
        # Mock os.path.exists to return True
        with patch('os.path.exists', return_value=True):
            result = await service.get_evidence_path("test-match-1")
        
        # Assertions
        assert result == "/path/to/evidence.jpg"
        mock_match_crud.get_match.assert_called_once_with("test-match-1")
    
    @pytest.mark.asyncio
    async def test_get_evidence_path_file_not_exists(self, service, mock_match_crud):
        """Test get_evidence_path when file doesn't exist"""
        # Setup mock data
        mock_match = MockMatch(evidence_path="/path/to/nonexistent.jpg")
        mock_match_crud.get_match.return_value = mock_match
        
        # Mock os.path.exists to return False
        with patch('os.path.exists', return_value=False):
            result = await service.get_evidence_path("test-match-1")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_evidence_path_no_evidence(self, service, mock_match_crud):
        """Test get_evidence_path when match has no evidence path"""
        # Setup mock data
        mock_match = MockMatch(evidence_path=None)
        mock_match_crud.get_match.return_value = mock_match
        
        result = await service.get_evidence_path("test-match-1")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_stats_success(self, service, mock_database):
        """Test successful get_stats operation"""
        # Setup mock data
        mock_database.fetch_val.side_effect = [100, 500, 50, 5000, 25, 10]
        
        # Call the method
        result = await service.get_stats()
        
        # Assertions
        assert result["products"] == 100
        assert result["product_images"] == 500
        assert result["videos"] == 50
        assert result["video_frames"] == 5000
        assert result["matches"] == 25
        assert result["jobs"] == 10
        
        # Verify all queries were made
        assert mock_database.fetch_val.call_count == 6
    
    @pytest.mark.asyncio
    async def test_get_stats_database_error(self, service, mock_database):
        """Test get_stats with database error"""
        mock_database.fetch_val.side_effect = Exception("Database error")
        
        with pytest.raises(ServiceError) as exc_info:
            await service.get_stats()
        
        assert "Failed to get stats" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_enrich_match_data_success(self, service, mock_product_crud, mock_video_crud):
        """Test successful _enrich_match_data operation"""
        # Setup mock data
        mock_match = MockMatch()
        mock_product = MockProduct()
        mock_video = MockVideo()
        
        mock_product_crud.get_product.return_value = mock_product
        mock_video_crud.get_video.return_value = mock_video
        
        # Call the private method
        result = await service._enrich_match_data(mock_match, None, "test-correlation-id")
        
        # Assertions
        assert result is not None
        assert result["match_id"] == "test-match-1"
        assert result["product_title"] == "Test Product"
        assert result["video_title"] == "Test Video"
    
    @pytest.mark.asyncio
    async def test_enrich_match_data_with_industry_filter(self, service, mock_product_crud, mock_video_crud):
        """Test _enrich_match_data with industry filter"""
        # Setup mock data
        mock_match = MockMatch()
        mock_product = MockProduct(title="Electronics Product")
        mock_video = MockVideo()
        
        mock_product_crud.get_product.return_value = mock_product
        mock_video_crud.get_video.return_value = mock_video
        
        # Test with matching industry
        result = await service._enrich_match_data(mock_match, "electronics", "test-correlation-id")
        assert result is not None
        
        # Test with non-matching industry
        result = await service._enrich_match_data(mock_match, "clothing", "test-correlation-id")
        assert result is None
    
    def test_format_product_details(self, service):
        """Test _format_product_details method"""
        mock_product = MockProduct()
        mock_product.created_at = datetime(2024, 1, 1)
        
        result = service._format_product_details(mock_product, 5)
        
        assert result["product_id"] == "test-product-1"
        assert result["title"] == "Test Product"
        assert result["image_count"] == 5
        assert "created_at" in result
    
    def test_format_video_details(self, service):
        """Test _format_video_details method"""
        mock_video = MockVideo()
        mock_video.created_at = datetime(2024, 1, 1)
        mock_video.published_at = datetime(2024, 1, 1)
        
        result = service._format_video_details(mock_video, 100)
        
        assert result["video_id"] == "test-video-1"
        assert result["title"] == "Test Video"
        assert result["frame_count"] == 100
        assert "created_at" in result
        assert "published_at" in result
    
    def test_format_match_details(self, service):
        """Test _format_match_details method"""
        mock_match = MockMatch()
        mock_match.created_at = datetime(2024, 1, 1)
        mock_product = MockProduct()
        mock_product.created_at = datetime(2024, 1, 1)
        mock_video = MockVideo()
        mock_video.created_at = datetime(2024, 1, 1)
        mock_video.published_at = datetime(2024, 1, 1)
        
        result = service._format_match_details(mock_match, mock_product, mock_video, 5, 100)
        
        assert result["match_id"] == "test-match-1"
        assert "product" in result
        assert "video" in result
        assert result["product"]["image_count"] == 5
        assert result["video"]["frame_count"] == 100