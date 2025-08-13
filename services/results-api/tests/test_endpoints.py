import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from handlers.results_handler import ResultsHandler
from services.service import ResultsService
from common_py.models import Product, Video, Match

@pytest.fixture
def mock_service():
    return AsyncMock(spec=ResultsService)

@pytest.fixture
def app(mock_service):
    handler = ResultsHandler.__new__(ResultsHandler)  # Create instance without calling __init__
    handler.service = mock_service
    handler.app = FastAPI(title="Results API", version="1.0.0")
    
    # Register routes manually
    handler.app.add_api_route("/results", handler.get_results, methods=["GET"])
    handler.app.add_api_route("/products/{product_id}", handler.get_product, methods=["GET"])
    handler.app.add_api_route("/videos/{video_id}", handler.get_video, methods=["GET"])
    handler.app.add_api_route("/matches/{match_id}", handler.get_match, methods=["GET"])
    handler.app.add_api_route("/evidence/{match_id}", handler.get_evidence_image, methods=["GET"])
    handler.app.add_api_route("/stats", handler.get_stats, methods=["GET"])
    handler.app.add_api_route("/health", handler.health_check, methods=["GET"])
    
    return handler.app

@pytest.fixture
def client(app):
    return TestClient(app)

class TestResultsEndpoints:
    """Test suite for Results API endpoints"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    
    @pytest.mark.asyncio
    async def test_get_results(self, client, mock_service):
        """Test get results endpoint"""
        # Mock service response
        mock_service.get_results.return_value = [
            {
                "match_id": "match1",
                "job_id": "job1",
                "product_id": "prod1",
                "video_id": "vid1",
                "score": 0.95,
                "product_title": "Test Product",
                "video_title": "Test Video"
            }
        ]
        
        response = client.get("/results?min_score=0.9&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["match_id"] == "match1"
        assert data[0]["score"] == 0.95
    
    @pytest.mark.asyncio
    async def test_get_product_success(self, client, mock_service):
        """Test get product endpoint with existing product"""
        # Mock service response
        mock_service.get_product.return_value = {
            "product_id": "prod1",
            "title": "Test Product",
            "brand": "Test Brand",
            "url": "https://example.com/product",
            "image_count": 5
        }
        
        response = client.get("/products/prod1")
        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == "prod1"
        assert data["title"] == "Test Product"
        assert data["image_count"] == 5
    
    @pytest.mark.asyncio
    async def test_get_product_not_found(self, client, mock_service):
        """Test get product endpoint with non-existent product"""
        # Mock service to return None
        mock_service.get_product.return_value = None
        
        response = client.get("/products/nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "Product not found"
    
    @pytest.mark.asyncio
    async def test_get_video_success(self, client, mock_service):
        """Test get video endpoint with existing video"""
        # Mock service response
        mock_service.get_video.return_value = {
            "video_id": "vid1",
            "title": "Test Video",
            "platform": "youtube",
            "url": "https://youtube.com/watch?v=test",
            "frame_count": 100
        }
        
        response = client.get("/videos/vid1")
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "vid1"
        assert data["title"] == "Test Video"
        assert data["frame_count"] == 100
    
    @pytest.mark.asyncio
    async def test_get_video_not_found(self, client, mock_service):
        """Test get video endpoint with non-existent video"""
        # Mock service to return None
        mock_service.get_video.return_value = None
        
        response = client.get("/videos/nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "Video not found"
    
    @pytest.mark.asyncio
    async def test_get_match_success(self, client, mock_service):
        """Test get match endpoint with existing match"""
        # Mock service response
        mock_service.get_match.return_value = {
            "match_id": "match1",
            "job_id": "job1",
            "product": {
                "product_id": "prod1",
                "title": "Test Product"
            },
            "video": {
                "video_id": "vid1",
                "title": "Test Video"
            },
            "score": 0.95
        }
        
        response = client.get("/matches/match1")
        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == "match1"
        assert data["score"] == 0.95
        assert data["product"]["product_id"] == "prod1"
        assert data["video"]["video_id"] == "vid1"
    
    @pytest.mark.asyncio
    async def test_get_match_not_found(self, client, mock_service):
        """Test get match endpoint with non-existent match"""
        # Mock service to return None
        mock_service.get_match.return_value = None
        
        response = client.get("/matches/nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "Match not found"
    
    @pytest.mark.asyncio
    async def test_get_evidence_image_success(self, client, mock_service):
        """Test get evidence image endpoint with existing evidence"""
        # Mock service response
        mock_service.get_evidence_path.return_value = "/path/to/evidence.jpg"
        
        response = client.get("/evidence/match1")
        assert response.status_code == 200
        data = response.json()
        assert data["evidence_path"] == "/path/to/evidence.jpg"
    
    @pytest.mark.asyncio
    async def test_get_evidence_image_not_found(self, client, mock_service):
        """Test get evidence image endpoint with non-existent evidence"""
        # Mock service to return None
        mock_service.get_evidence_path.return_value = None
        
        response = client.get("/evidence/nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "Evidence image not found"
    
    @pytest.mark.asyncio
    async def test_get_stats(self, client, mock_service):
        """Test get stats endpoint"""
        # Mock service response
        mock_service.get_stats.return_value = {
            "products": 100,
            "videos": 50,
            "matches": 200
        }
        
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["products"] == 100
        assert data["videos"] == 50
        assert data["matches"] == 200