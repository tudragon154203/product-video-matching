"""
Integration tests for API endpoints.
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi import status

from tests.conftest import MockProduct, MockVideo, MockMatch


class TestResultsEndpoints:
    """Test results API endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_results_success(self, async_test_client, mock_results_service):
        """Test successful get results endpoint"""
        # Setup mock service response
        mock_results_service.get_results.return_value = [
            {
                "match_id": "test-match-1",
                "job_id": "test-job-1",
                "product_id": "test-product-1",
                "video_id": "test-video-1",
                "best_img_id": "test-img-1",
                "best_frame_id": "test-frame-1",
                "ts": 120.5,
                "score": 0.85,
                "evidence_path": "/path/to/evidence.jpg",
                "created_at": "2024-01-01T00:00:00Z",
                "product_title": "Test Product",
                "video_title": "Test Video",
                "video_platform": "youtube"
            }
        ]
        
        response = await async_test_client.get("/results")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["match_id"] == "test-match-1"
    
    @pytest.mark.asyncio
    async def test_get_results_with_filters(self, async_test_client, mock_results_service):
        """Test get results endpoint with query filters"""
        mock_results_service.get_results.return_value = []
        
        response = await async_test_client.get(
            "/results?industry=electronics&min_score=0.8&limit=50&offset=10"
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify service was called with correct parameters
        mock_results_service.get_results.assert_called_once_with(
            industry="electronics",
            min_score=0.8,
            job_id=None,
            limit=50,
            offset=10
        )
    
    @pytest.mark.asyncio
    async def test_get_results_validation_error(self, async_test_client):
        """Test get results endpoint with invalid parameters"""
        response = await async_test_client.get("/results?min_score=1.5")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_get_product_success(self, async_test_client, mock_results_service):
        """Test successful get product endpoint"""
        # Setup mock service response
        mock_results_service.get_product.return_value = {
            "product_id": "test-product-1",
            "src": "amazon",
            "asin_or_itemid": "B123456789",
            "title": "Test Product",
            "brand": "Test Brand",
            "url": "https://amazon.com/test-product",
            "created_at": "2024-01-01T00:00:00Z",
            "image_count": 5
        }
        
        response = await async_test_client.get("/products/test-product-1")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["product_id"] == "test-product-1"
        assert data["title"] == "Test Product"
    
    @pytest.mark.asyncio
    async def test_get_product_not_found(self, async_test_client, mock_results_service):
        """Test get product endpoint when product not found"""
        mock_results_service.get_product.return_value = None
        
        response = await async_test_client.get("/products/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error_code"] == "RESOURCE_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_get_video_success(self, async_test_client, mock_results_service):
        """Test successful get video endpoint"""
        # Setup mock service response
        mock_results_service.get_video.return_value = {
            "video_id": "test-video-1",
            "platform": "youtube",
            "url": "https://youtube.com/watch?v=test",
            "title": "Test Video",
            "duration_s": 300,
            "published_at": "2024-01-01T00:00:00Z",
            "created_at": "2024-01-01T00:00:00Z",
            "frame_count": 100
        }
        
        response = await async_test_client.get("/videos/test-video-1")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["video_id"] == "test-video-1"
        assert data["title"] == "Test Video"
    
    @pytest.mark.asyncio
    async def test_get_video_not_found(self, async_test_client, mock_results_service):
        """Test get video endpoint when video not found"""
        mock_results_service.get_video.return_value = None
        
        response = await async_test_client.get("/videos/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error_code"] == "RESOURCE_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_get_match_success(self, async_test_client, mock_results_service):
        """Test successful get match endpoint"""
        # Setup mock service response
        mock_results_service.get_match.return_value = {
            "match_id": "test-match-1",
            "job_id": "test-job-1",
            "best_img_id": "test-img-1",
            "best_frame_id": "test-frame-1",
            "ts": 120.5,
            "score": 0.85,
            "evidence_path": "/path/to/evidence.jpg",
            "created_at": "2024-01-01T00:00:00Z",
            "product": {
                "product_id": "test-product-1",
                "title": "Test Product",
                "image_count": 5,
                "created_at": "2024-01-01T00:00:00Z"
            },
            "video": {
                "video_id": "test-video-1",
                "title": "Test Video",
                "frame_count": 100,
                "created_at": "2024-01-01T00:00:00Z"
            }
        }
        
        response = await async_test_client.get("/matches/test-match-1")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["match_id"] == "test-match-1"
        assert "product" in data
        assert "video" in data
    
    @pytest.mark.asyncio
    async def test_get_match_not_found(self, async_test_client, mock_results_service):
        """Test get match endpoint when match not found"""
        mock_results_service.get_match.return_value = None
        
        response = await async_test_client.get("/matches/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error_code"] == "RESOURCE_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_get_evidence_success(self, async_test_client, mock_results_service):
        """Test successful get evidence endpoint"""
        mock_results_service.get_evidence_path.return_value = "/path/to/evidence.jpg"
        
        response = await async_test_client.get("/evidence/test-match-1")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["evidence_path"] == "/path/to/evidence.jpg"
    
    @pytest.mark.asyncio
    async def test_get_evidence_not_found(self, async_test_client, mock_results_service):
        """Test get evidence endpoint when evidence not found"""
        mock_results_service.get_evidence_path.return_value = None
        
        response = await async_test_client.get("/evidence/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error_code"] == "RESOURCE_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_get_stats_success(self, async_test_client, mock_results_service):
        """Test successful get stats endpoint"""
        mock_results_service.get_stats.return_value = {
            "products": 100,
            "product_images": 500,
            "videos": 50,
            "video_frames": 5000,
            "matches": 25,
            "jobs": 10
        }
        
        response = await async_test_client.get("/stats")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["products"] == 100
        assert data["matches"] == 25
    
    @pytest.mark.asyncio
    async def test_health_check(self, async_test_client):
        """Test health check endpoint"""
        response = await async_test_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"


class TestRootEndpoint:
    """Test root endpoint"""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, async_test_client):
        """Test root endpoint"""
        response = await async_test_client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "status" in data


class TestErrorHandling:
    """Test error handling in API endpoints"""
    
    @pytest.mark.asyncio
    async def test_service_error_handling(self, async_test_client, mock_results_service):
        """Test service error handling"""
        from core.exceptions import ServiceError
        
        mock_results_service.get_results.side_effect = ServiceError("Service unavailable")
        
        response = await async_test_client.get("/results")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["error_code"] == "SERVICE_ERROR"
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, async_test_client, mock_results_service):
        """Test database error handling"""
        from core.exceptions import DatabaseError
        
        mock_results_service.get_product.side_effect = DatabaseError("Database connection failed")
        
        response = await async_test_client.get("/products/test-product-1")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["error_code"] == "DATABASE_ERROR"
    
