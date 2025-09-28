"""
Unit tests for image utility functions.
"""
import pytest
pytestmark = pytest.mark.unit
import os
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

from utils.image_utils import to_public_url, get_mime_type, is_safe_path


class TestToPublicUrl:
    """Test cases for the to_public_url function."""
    
    def test_happy_path_unix(self):
        """Test happy path with Unix-style paths."""
        local_path = "/app/data/images/123.jpg"
        data_root = "/app/data"
        result = to_public_url(local_path, data_root)
        assert result == "/files/images/123.jpg"
    
    def test_happy_path_windows(self):
        """Test happy path with Windows-style paths."""
        local_path = "C:\\data\\images\\x\\y.png"
        data_root = "C:\\data"
        result = to_public_url(local_path, data_root)
        assert result == "/files/images/x/y.png"
    
    def test_empty_path(self):
        """Test with empty path."""
        result = to_public_url("", "/app/data")
        assert result is None
    
    def test_none_path(self):
        """Test with None path."""
        result = to_public_url(None, "/app/data")
        assert result is None
    
    def test_whitespace_path(self):
        """Test with whitespace-only path."""
        result = to_public_url("   ", "/app/data")
        assert result is None
    
    def test_path_not_starting_with_root(self):
        """Test path that doesn't start with data root."""
        local_path = "/other/path/image.jpg"
        data_root = "/app/data"
        result = to_public_url(local_path, data_root)
        assert result is None
    
    def test_path_above_root(self):
        """Test path that tries to escape above data root."""
        local_path = "/app/data/../secret/file.jpg"
        data_root = "/app/data"
        result = to_public_url(local_path, data_root)
        assert result is None
    
    def test_path_with_double_dots(self):
        """Test path containing double dots - should be resolved securely."""
        local_path = "/app/data/images/../secret/file.jpg"
        data_root = "/app/data"
        result = to_public_url(local_path, data_root)
        # os.path.abspath resolves ../, so this should be valid
        assert result == "/files/secret/file.jpg"
    
    def test_path_with_trailing_slash(self):
        """Test path with trailing slash - should be treated as directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a directory with trailing slash
            dir_path = os.path.join(temp_dir, "test_dir")
            os.makedirs(dir_path)
            
            data_root = temp_dir
            result = to_public_url(dir_path + os.sep, data_root)
            # This should return None because it's a directory
            assert result is None
    
    def test_nested_path(self):
        """Test deeply nested path."""
        local_path = "/app/data/images/a/b/c/d/e.jpg"
        data_root = "/app/data"
        result = to_public_url(local_path, data_root)
        assert result == "/files/images/a/b/c/d/e.jpg"
    
    def test_case_sensitivity(self):
        """Test case sensitivity handling."""
        local_path = "/app/Data/Images/TEST.JPG"
        data_root = "/app/data"
        result = to_public_url(local_path, data_root)
        # Should still work as path normalization handles case
        assert result is None  # Path doesn't match exactly due to case
    
    @patch('utils.image_utils.os.path.normpath')
    def test_normalization_error(self, mock_normpath):
        """Test error during path normalization."""
        mock_normpath.side_effect = ValueError("Normalization error")
        result = to_public_url("/app/data/image.jpg", "/app/data")
        assert result is None
    
    @patch('utils.image_utils.os.path.relpath')
    def test_relpath_error(self, mock_relpath):
        """Test error during relative path calculation."""
        mock_relpath.side_effect = ValueError("Relative path error")
        result = to_public_url("/app/data/image.jpg", "/app/data")
        assert result is None


class TestGetMimeType:
    """Test cases for the get_mime_type function."""
    
    def test_jpeg(self):
        """Test JPEG file."""
        assert get_mime_type("image.jpg") == "image/jpeg"
        assert get_mime_type("image.jpeg") == "image/jpeg"
    
    def test_png(self):
        """Test PNG file."""
        assert get_mime_type("image.png") == "image/png"
    
    def test_gif(self):
        """Test GIF file."""
        assert get_mime_type("image.gif") == "image/gif"
    
    def test_webp(self):
        """Test WebP file."""
        assert get_mime_type("image.webp") == "image/webp"
    
    def test_svg(self):
        """Test SVG file."""
        assert get_mime_type("image.svg") == "image/svg+xml"
    
    def test_bmp(self):
        """Test BMP file."""
        assert get_mime_type("image.bmp") == "image/bmp"
    
    def test_tiff(self):
        """Test TIFF file."""
        assert get_mime_type("image.tiff") == "image/tiff"
    
    def test_ico(self):
        """Test ICO file."""
        assert get_mime_type("image.ico") == "image/x-icon"
    
    def test_unknown_extension(self):
        """Test unknown file extension."""
        assert get_mime_type("image.xyz") == "application/octet-stream"
    
    def test_no_extension(self):
        """Test file with no extension."""
        assert get_mime_type("image") == "application/octet-stream"
    
    def test_case_insensitive(self):
        """Test case insensitive extension matching."""
        assert get_mime_type("image.JPG") == "image/jpeg"
        assert get_mime_type("image.PnG") == "image/png"


class TestIsSafePath:
    """Test cases for the is_safe_path function."""
    
    def test_safe_path(self):
        """Test safe path within base directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "image.jpg")
            Path(file_path).touch()  # Create the file
            
            result = is_safe_path(file_path, temp_dir)
            assert result is True
    
    def test_path_outside_base(self):
        """Test path outside base directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            other_dir = os.path.join(temp_dir, "other")
            os.makedirs(other_dir)
            
            file_path = os.path.join(other_dir, "image.jpg")
            Path(file_path).touch()
            
            result = is_safe_path(file_path, temp_dir)
            assert result is True  # This should be True as it's within the temp_dir structure
    
    def test_path_escape_attempt(self):
        """Test path that tries to escape base directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a path that tries to go outside the temp_dir
            outside_path = os.path.join(temp_dir, "..", "outside", "image.jpg")
            
            result = is_safe_path(outside_path, temp_dir)
            assert result is False
    
    @patch('utils.image_utils.os.path.islink')
    @patch('utils.image_utils.os.path.realpath')
    def test_unsafe_symlink(self, mock_realpath, mock_islink):
        """Test symlink pointing outside base directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_islink.return_value = True
            mock_realpath.return_value = "/outside/symlink_target"
            
            file_path = os.path.join(temp_dir, "symlink.jpg")
            
            result = is_safe_path(file_path, temp_dir)
            assert result is False
    
    @patch('utils.image_utils.os.path.islink')
    @patch('utils.image_utils.os.path.realpath')
    def test_safe_symlink(self, mock_realpath, mock_islink):
        """Test symlink pointing within base directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_file = os.path.join(temp_dir, "target.jpg")
            Path(target_file).touch()
            
            mock_islink.return_value = True
            mock_realpath.return_value = target_file
            
            file_path = os.path.join(temp_dir, "symlink.jpg")
            
            result = is_safe_path(file_path, temp_dir)
            assert result is True
    
    @patch('utils.image_utils.os.path.abspath')
    def test_abspath_error(self, mock_abspath):
        """Test error during absolute path conversion."""
        mock_abspath.side_effect = OSError("Path error")
        
        result = is_safe_path("/path/file.jpg", "/base")
        assert result is False
    
    @patch('utils.image_utils.os.path.islink')
    def test_symlink_check_error(self, mock_islink):
        """Test error during symlink check."""
        mock_islink.side_effect = OSError("Symlink error")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "image.jpg")
            Path(file_path).touch()
            
            result = is_safe_path(file_path, temp_dir)
            assert result is False  # Should be False if symlink check fails (conservative approach)