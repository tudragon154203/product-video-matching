import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch
from platform_crawler.tiktok.tiktok_downloader import TikTokDownloader


class TestDownloadLogic:
    """Test download logic for TikTokDownloader"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_root = Path(tempfile.mkdtemp(prefix="video_crawler_unit_tests_"))
        self.video_dir = self.temp_root / "videos"
        self.keyframe_dir = self.temp_root / "keyframes"
        self.config = {
            'TIKTOK_VIDEO_STORAGE_PATH': str(self.video_dir),
            'TIKTOK_KEYFRAME_STORAGE_PATH': str(self.keyframe_dir),
            'retries': 3,
            'timeout': 30
        }
        self.downloader = TikTokDownloader(self.config)

    def teardown_method(self):
        """Clean up temp directories created for tests"""
        if hasattr(self, "temp_root"):
            shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_config_defaults(self):
        """Test default configuration values"""
        # Test with minimal config
        minimal_config = {}
        downloader = TikTokDownloader(minimal_config)

        # Should use defaults
        assert downloader.retries == 3
        assert downloader.timeout == 30
        expected_video_path = (Path(tempfile.gettempdir()) / "videos" / "tiktok").resolve()
        expected_keyframe_path = (Path(tempfile.gettempdir()) / "keyframes" / "tiktok").resolve()
        assert Path(downloader.video_storage_path) == expected_video_path
        assert Path(downloader.keyframe_storage_path) == expected_keyframe_path

    def test_custom_config(self):
        """Test custom configuration values"""
        custom_config = {
            'retries': 5,
            'timeout': 60,
            'TIKTOK_VIDEO_STORAGE_PATH': '/custom/videos',
            'TIKTOK_KEYFRAME_STORAGE_PATH': '/custom/keyframes'
        }
        downloader = TikTokDownloader(custom_config)

        # Should use custom values
        assert downloader.retries == 5
        assert downloader.timeout == 60
        assert Path(downloader.video_storage_path) == Path('/custom/videos').resolve()
        assert Path(downloader.keyframe_storage_path) == Path('/custom/keyframes').resolve()

    def test_directory_creation(self):
        """Test that storage directories are created"""
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            config = {
                'TIKTOK_VIDEO_STORAGE_PATH': '/new/videos',
                'TIKTOK_KEYFRAME_STORAGE_PATH': '/new/keyframes'
            }
            TikTokDownloader(config)

            assert mock_mkdir.call_count == 2
            # Verify all calls have the correct kwargs
            for call in mock_mkdir.call_args_list:
                assert call.kwargs == {'parents': True, 'exist_ok': True}
