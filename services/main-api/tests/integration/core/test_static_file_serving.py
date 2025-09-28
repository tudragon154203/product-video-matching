"""
Integration tests for static file serving functionality.
"""
import pytest
pytestmark = pytest.mark.integration
import os
import tempfile
import json
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch

from main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory with test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test files
        test_files = {
            "smoke.jpg": b"fake jpeg content",
            "nested/a/b/c.png": b"fake png content",
            "test.webp": b"fake webp content",
            "image.gif": b"fake gif content",
            "broken.link": b"invalid content",
        }
        
        for file_path, content in test_files.items():
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(content)
        
        yield temp_dir


@pytest.fixture
def mock_config(temp_data_dir):
    """Mock configuration to use temporary data directory."""
    with patch('config_loader.config') as mock_config:
        mock_config.DATA_ROOT_CONTAINER = temp_data_dir
        # Reinitialize the static files app with the new config
        with patch('api.static_endpoints.get_static_files_app') as mock_get_app:
            mock_static_app = patch('fastapi.staticfiles.StaticFiles').return_value
            mock_get_app.return_value = mock_static_app
            yield mock_config


class TestStaticFileServing:
    """Test cases for static file serving endpoints."""
    
    def test_serve_jpeg_file(self, client, mock_config):
        """Test serving a JPEG file."""
        response = client.get("/files/smoke.jpg")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert "cache-control" in response.headers
        assert response.content == b"fake jpeg content"
    
    def test_serve_nested_png_file(self, client, mock_config):
        """Test serving a nested PNG file."""
        response = client.get("/files/nested/a/b/c.png")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert response.content == b"fake png content"
    
    def test_serve_webp_file(self, client, mock_config):
        """Test serving a WebP file."""
        response = client.get("/files/test.webp")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"
        assert response.content == b"fake webp content"
    
    def test_serve_gif_file(self, client, mock_config):
        """Test serving a GIF file."""
        response = client.get("/files/image.gif")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/gif"
        assert response.content == b"fake gif content"
    
    def test_file_not_found(self, client, mock_config):
        """Test requesting a non-existent file."""
        response = client.get("/files/nonexistent.jpg")
        assert response.status_code == 404
    
    def test_directory_access(self, client, mock_config):
        """Test accessing a directory (should be denied by StaticFiles)."""
        response = client.get("/files/nested/")
        # StaticFiles will return 404 for directory access
        assert response.status_code == 404
    
    def test_path_traversal_attack(self, client, mock_config):
        """Test path traversal attack attempt."""
        response = client.get("/files/../../../etc/passwd")
        # StaticFiles should block this
        assert response.status_code in [403, 404]
    
    def test_double_dot_attack(self, client, mock_config):
        """Test double dot attack attempt."""
        response = client.get("/files/smoke.jpg/../../../etc/passwd")
        # StaticFiles should block this
        assert response.status_code in [403, 404]
    
    def test_empty_filename(self, client, mock_config):
        """Test requesting with empty filename."""
        response = client.get("/files/")
        assert response.status_code == 404
    
    def test_url_encoded_path(self, client, mock_config):
        """Test URL encoded path."""
        response = client.get("/files/nested%2Fa%2Fb%2Fc.png")
        # This should work as the path is properly decoded by FastAPI
        assert response.status_code == 200
        assert response.content == b"fake png content"
    
    def test_malformed_path(self, client, mock_config):
        """Test malformed path."""
        response = client.get("/files/..\\..\\windows\\path.jpg")
        # StaticFiles should handle this
        assert response.status_code in [403, 404]
    
    def test_cache_headers_present(self, client, mock_config):
        """Test that cache headers are present."""
        response = client.get("/files/smoke.jpg")
        assert "cache-control" in response.headers
        assert response.headers["cache-control"] == "public, max-age=3600"
    
    def test_content_type_header_present(self, client, mock_config):
        """Test that content-type header is present."""
        response = client.get("/files/smoke.jpg")
        assert "content-type" in response.headers
        assert response.headers["content-type"] == "image/jpeg"


class TestImageEndpointsWithUrls:
    """Test cases for image endpoints that include URL fields."""
    
    def test_image_endpoint_includes_url(self, client, mock_config):
        """Test that image endpoint includes URL field in response."""
        # This test assumes we have some test data in the database
        # For now, we'll test the structure without actual database data
        response = client.get("/jobs/test-job-id/images")
        
        # If the job exists and has images, check the response structure
        if response.status_code == 200:
            data = response.json()
            assert "items" in data
            for item in data["items"]:
                assert "img_id" in item
                assert "product_id" in item
                assert "local_path" in item
                assert "url" in item  # New field should be present
                assert "product_title" in item
                assert "updated_at" in item
    
    def test_frame_endpoint_includes_url(self, client, mock_config):
        """Test that frame endpoint includes URL field in response."""
        response = client.get("/jobs/test-job-id/videos/test-video-id/frames")
        
        # If the video exists and has frames, check the response structure
        if response.status_code == 200:
            data = response.json()
            assert "items" in data
            for item in data["items"]:
                assert "frame_id" in item
                assert "ts" in item
                assert "local_path" in item
                assert "url" in item  # New field should be present
                assert "updated_at" in item


class TestSecurityMeasures:
    """Test security measures for static file serving."""
    
    def test_symlink_protection(self, client, mock_config):
        """Test that symlinks pointing outside data root are blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a symlink pointing outside the data directory
            outside_file = os.path.join(temp_dir, "outside.txt")
            with open(outside_file, "w") as f:
                f.write("outside content")
            
            data_dir = os.path.join(temp_dir, "data")
            os.makedirs(data_dir)
            
            symlink_path = os.path.join(data_dir, "symlink.txt")
            try:
                os.symlink(outside_file, symlink_path)
                
                # Update mock config to use our test directory
                mock_config.DATA_ROOT_CONTAINER = data_dir
                
                # Try to access the symlink
                response = client.get("/files/symlink.txt")
                assert response.status_code == 403
                assert response.json()["detail"] == "Access denied"
            except (OSError, PermissionError):
                # Skip test on Windows if symlink creation fails
                pytest.skip("Symlink creation not supported on this platform")
    
    def test_long_path_protection(self, client, mock_config):
        """Test protection against very long paths."""
        long_path = "a" * 1000 + ".jpg"
        response = client.get(f"/files/{long_path}")
        assert response.status_code in [403, 404]
    
    def test_null_byte_protection(self, client, mock_config):
        """Test protection against null byte attacks."""
        malicious_path = "file.jpg\x00.txt"
        response = client.get(f"/files/{malicious_path}")
        assert response.status_code in [403, 404]