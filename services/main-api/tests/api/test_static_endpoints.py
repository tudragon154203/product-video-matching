"""
Unit tests for static file serving endpoints.
Minimal test cases focusing on core functionality.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
import os
from pathlib import Path

from api.static_endpoints import router, get_static_file_service
from services.static_file_service import StaticFileService


@pytest.fixture
def mock_static_file_service():
    """Mock static file service"""
    service = MagicMock()
    service.get_secure_file_path = MagicMock()
    service.validate_file_access = MagicMock()
    service.get_content_type = MagicMock()
    service.log_request = MagicMock()
    service.data_root = Path("/tmp/test_data")
    return service


@pytest.fixture
def test_app(mock_static_file_service):
    """Create test FastAPI app with mocked dependencies"""
    app = FastAPI()
    app.include_router(router)
    
    # Override dependency
    app.dependency_overrides[get_static_file_service] = lambda: mock_static_file_service
    
    return app


@pytest.fixture
def client(test_app):
    """Create test client"""
    return TestClient(test_app)


def test_serve_static_file_success(client, mock_static_file_service):
    """Test successful static file serving"""
    # Setup mock response
    test_file_path = Path("/tmp/test_data/test.jpg")
    mock_static_file_service.get_secure_file_path.return_value = test_file_path
    mock_static_file_service.get_content_type.return_value = "image/jpeg"
    
    # We can't easily mock FileResponse, so we'll test that the endpoint
    # calls the service methods correctly by checking if they were called
    with patch('api.static_endpoints.FileResponse') as mock_file_response:
        mock_file_response.return_value = {"message": "File served"}
        
        # Execute
        response = client.get("/files/test.jpg")
        
        # Verify service methods were called
        mock_static_file_service.get_secure_file_path.assert_called_once_with("test.jpg")
        mock_static_file_service.validate_file_access.assert_called_once_with(test_file_path)
        mock_static_file_service.get_content_type.assert_called_once_with(test_file_path)
        
        # Verify response
        assert response.status_code == 200


def test_serve_static_file_not_found(client, mock_static_file_service):
    """Test static file not found"""
    # Setup mock to raise FileNotFoundError
    mock_static_file_service.get_secure_file_path.return_value = Path("/tmp/test_data/nonexistent.jpg")
    mock_static_file_service.validate_file_access.side_effect = FileNotFoundError("File not found")
    
    # Execute
    response = client.get("/files/nonexistent.jpg")
    
    # Verify
    assert response.status_code == 404
    assert "detail" in response.json()


def test_serve_static_file_internal_error(client, mock_static_file_service):
    """Test static file serving with internal error"""
    # Setup mock to raise generic exception
    mock_static_file_service.get_secure_file_path.side_effect = Exception("Internal error")
    
    # Execute
    response = client.get("/files/broken.jpg")
    
    # Verify
    assert response.status_code == 500
    assert "detail" in response.json()


def test_static_files_health_healthy(client, mock_static_file_service):
    """Test health check endpoint when service is healthy"""
    # Setup mock
    with patch('api.static_endpoints.os.path.exists', return_value=True):
        with patch('api.static_endpoints.os.listdir', return_value=['file1.jpg', 'file2.png']):
            # Execute
            response = client.get("/health")
            
            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["message"] == "Static files service is operational"
            assert "data_directory" in data
            assert data["file_count"] == 2


def test_static_files_health_directory_not_found(client, mock_static_file_service):
    """Test health check endpoint when data directory is not found"""
    # Setup mock
    with patch('api.static_endpoints.os.path.exists', return_value=False):
        # Execute
        response = client.get("/health")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["message"] == "Data directory not found"


def test_static_files_health_permission_error(client, mock_static_file_service):
    """Test health check endpoint when there's a permission error"""
    # Setup mock
    with patch('api.static_endpoints.os.path.exists', return_value=True):
        with patch('api.static_endpoints.os.listdir', side_effect=PermissionError("Permission denied")):
            # Execute
            response = client.get("/health")
            
            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert data["message"] == "Permission denied on data directory"


def test_static_files_health_internal_error(client, mock_static_file_service):
    """Test health check endpoint with internal error"""
    # Setup mock
    with patch('api.static_endpoints.os.path.exists', side_effect=Exception("Internal error")):
        # Execute
        response = client.get("/health")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Health check failed" in data["message"]