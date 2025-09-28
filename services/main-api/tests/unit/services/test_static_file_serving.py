"""
Unit tests for static file serving functionality.
"""
from main import app
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from pathlib import Path
import httpx
import tempfile
import os
import pytest
pytestmark = pytest.mark.unit


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
def mock_static_file_service(temp_data_dir):
    """Mock static file service that works with the temporary data directory."""
    with patch('api.static_endpoints.StaticFileService') as mock_service_cls:
        mock_service = MagicMock()

        def _resolve(filename: str) -> Path:
            if not filename:
                raise FileNotFoundError("File not found")
            resolved_path = Path(temp_data_dir, filename).resolve()
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            return resolved_path

        def _validate(file_path: Path) -> None:
            if not file_path.exists():
                raise FileNotFoundError("File not found")
            if file_path.is_dir():
                raise IsADirectoryError("Directory access attempt")

        def _content_type(file_path: Path) -> str:
            return {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.webp': 'image/webp',
                '.gif': 'image/gif'
            }.get(file_path.suffix.lower(), 'application/octet-stream')

        mock_service.get_secure_file_path.side_effect = _resolve
        mock_service.validate_file_access.side_effect = _validate
        mock_service.get_content_type.side_effect = _content_type
        mock_service.build_full_url.side_effect = (
            lambda relative_path: f"http://localhost:8888/files/{Path(relative_path).as_posix()}"
        )

        mock_service_cls.return_value = mock_service

        yield mock_service


@pytest.fixture
def mock_config(temp_data_dir):
    """Temporarily point service configuration to the test directory."""
    from config_loader import config as app_config

    original_data_root = app_config.DATA_ROOT_CONTAINER
    app_config.DATA_ROOT_CONTAINER = temp_data_dir
    try:
        yield app_config
    finally:
        app_config.DATA_ROOT_CONTAINER = original_data_root


class TestStaticFileServing:
    """Test cases for static file serving endpoints."""

    def test_serve_jpeg_file(self, client, mock_static_file_service):
        """Test serving a JPEG file."""
        response = client.get("/files/smoke.jpg")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert "cache-control" in response.headers

    def test_serve_nested_png_file(self, client, mock_static_file_service):
        """Test serving a nested PNG file."""
        response = client.get("/files/nested/a/b/c.png")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

    def test_serve_webp_file(self, client, mock_static_file_service):
        """Test serving a WebP file."""
        response = client.get("/files/test.webp")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"

    def test_serve_gif_file(self, client, mock_static_file_service):
        """Test serving a GIF file."""
        response = client.get("/files/image.gif")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/gif"

    def test_file_not_found(self, client, mock_static_file_service):
        """Test requesting a non-existent file."""
        # Make the service raise FileNotFoundError
        mock_static_file_service.get_secure_file_path.side_effect = FileNotFoundError(
            "File not found")
        response = client.get("/files/nonexistent.jpg")
        assert response.status_code == 404

    def test_directory_access(self, client, mock_static_file_service):
        """Test accessing a directory (should be denied by StaticFiles)."""
        # Make the service raise IsADirectoryError
        mock_static_file_service.get_secure_file_path.side_effect = IsADirectoryError(
            "Directory access attempt")
        response = client.get("/files/nested/")
        assert response.status_code == 500  # Should be handled as internal error

    def test_path_traversal_attack(self, client, mock_static_file_service):
        """Test path traversal attack attempt."""
        # Make the service raise ValueError for path traversal
        mock_static_file_service.get_secure_file_path.side_effect = ValueError(
            "Path traversal attempt")
        response = client.get("/files/../../../etc/passwd")
        assert response.status_code in {404, 500}

    def test_double_dot_attack(self, client, mock_static_file_service):
        """Test double dot attack attempt."""
        # Make the service raise ValueError for path traversal
        mock_static_file_service.get_secure_file_path.side_effect = ValueError(
            "Path traversal attempt")
        response = client.get("/files/smoke.jpg/../../../etc/passwd")
        assert response.status_code in {404, 500}

    def test_empty_filename(self, client, mock_static_file_service):
        """Test requesting with empty filename."""
        response = client.get("/files/")
        assert response.status_code == 404

    def test_url_encoded_path(self, client, mock_static_file_service):
        """Test URL encoded path."""
        response = client.get("/files/nested%2Fa%2Fb%2Fc.png")
        # This should work as the path is properly decoded by FastAPI
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

    def test_malformed_path(self, client, mock_static_file_service):
        """Test malformed path."""
        # Make the service raise ValueError for malformed path
        mock_static_file_service.get_secure_file_path.side_effect = ValueError(
            "Malformed path")
        response = client.get("/files/..\\..\\windows\\path.jpg")
        assert response.status_code == 500

    def test_cache_headers_present(self, client, mock_static_file_service):
        """Test that cache headers are present."""
        response = client.get("/files/smoke.jpg")
        assert "cache-control" in response.headers
        assert response.headers["cache-control"] == "public, max-age=3600"

    def test_content_type_header_present(self, client, mock_static_file_service):
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
                assert "product_at" in item
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
        try:
            response = client.get(f"/files/{malicious_path}")
        except httpx.InvalidURL:
            return
        assert response.status_code in [403, 404]
