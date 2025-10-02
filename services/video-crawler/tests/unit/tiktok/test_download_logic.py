import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
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

    def test_size_limit_large_file_fail(self):
        """Test that files larger than 500MB fail validation"""
        with patch('yt_dlp.YoutubeDL') as mock_ydl:
            # Mock the download to create a large file
            with tempfile.NamedTemporaryFile(suffix='.mp4',
                                             delete=False,
                                             dir=str(self.video_dir)
                                             ) as temp_file:
                # Create a file larger than 500MB (simulate)
                temp_file.write(b'x' * (501 * 1024 * 1024))  # 501MB
                temp_file_path = temp_file.name

            # Mock yt_dlp to create the large file
            mock_ydl_instance = Mock()
            mock_ydl.return_value.__enter__.return_value = mock_ydl_instance

            # Mock os.path.exists and os.path.getsize to return our temp file
            with patch('os.path.exists', return_value=True), \
                    patch('os.path.getsize', return_value=501 * 1024 * 1024):

                result = self.downloader.download_video("https://example.com/video", "test_id")

                # Should return None due to size limit
                assert result is None

                # Verify the file was removed due to size limit
                assert not os.path.exists(temp_file_path)

        # Clean up
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    def test_retry_logic_with_backoff(self):
        """Test retry logic with exponential backoff"""
        with patch('yt_dlp.YoutubeDL') as mock_ydl, \
                patch('time.sleep') as mock_sleep:

            # Mock yt_dlp to fail twice then succeed
            mock_ydl_instance = Mock()
            mock_ydl.return_value.__enter__.return_value = mock_ydl_instance

            # Track download calls
            download_calls = []

            def mock_download(urls):
                download_calls.append(len(download_calls))
                if len(download_calls) < 3:  # Fail first 2 attempts
                    raise Exception("Network error")
                # Create a valid file on 3rd attempt
                with open(os.path.join(self.config['TIKTOK_VIDEO_STORAGE_PATH'], "test_id.mp4"), 'w') as f:
                    f.write("valid content")

            mock_ydl_instance.download = mock_download

            # Mock file validation
            with patch('os.path.exists', return_value=True), \
                    patch('os.path.getsize', return_value=1024):

                result = self.downloader.download_video("https://example.com/video", "test_id")

                # Should succeed after retries
                assert result is not None
                assert result.endswith("test_id.mp4")

                # Verify exponential backoff was used (sleep calls: 1s, 2s)
                assert mock_sleep.call_count == 2
                assert mock_sleep.call_args_list[0][0][0] == 1  # 2^0 = 1
                assert mock_sleep.call_args_list[1][0][0] == 2  # 2^1 = 2

    def test_validation_missing_file_fail(self):
        """Test validation fails when file is missing or empty"""
        with patch('yt_dlp.YoutubeDL') as mock_ydl:
            # Mock yt_dlp to "succeed" but not create a file
            mock_ydl_instance = Mock()
            mock_ydl.return_value.__enter__.return_value = mock_ydl_instance
            mock_ydl_instance.download = Mock()  # Don't create any file

            # Test case 1: File doesn't exist
            with patch('os.path.exists', return_value=False):
                result = self.downloader.download_video("https://example.com/video", "test_id")
                assert result is None

            # Test case 2: File exists but is empty
            with patch('os.path.exists', return_value=True), \
                    patch('os.path.getsize', return_value=0):
                result = self.downloader.download_video("https://example.com/video", "test_id")
                assert result is None

    def test_successful_download(self):
        """Test successful download with valid file"""
        with patch('yt_dlp.YoutubeDL') as mock_ydl:
            # Mock yt_dlp to succeed
            mock_ydl_instance = Mock()
            mock_ydl.return_value.__enter__.return_value = mock_ydl_instance
            mock_ydl_instance.download = Mock()

            # Mock successful file creation and validation
            with patch('os.path.exists', return_value=True), \
                    patch('os.path.getsize', return_value=1024 * 1024):  # 1MB file

                result = self.downloader.download_video("https://example.com/video", "test_id")

                # Should return the file path
                assert result is not None
                assert result.endswith("test_id.mp4")
                assert os.path.exists(result)

    def test_retry_exhaustion(self):
        """Test that retries are exhausted after max attempts"""
        with patch('yt_dlp.YoutubeDL') as mock_ydl, \
                patch('time.sleep') as mock_sleep:

            # Mock yt_dlp to always fail
            mock_ydl_instance = Mock()
            mock_ydl.return_value.__enter__.return_value = mock_ydl_instance
            mock_ydl_instance.download.side_effect = Exception("Persistent network error")

            result = self.downloader.download_video("https://example.com/video", "test_id")

            # Should return None after all retries
            assert result is None

            # Verify all retries were attempted
            assert mock_sleep.call_count == self.config['retries']

            # Verify exponential backoff sequence
            expected_sleep_times = [2**i for i in range(self.config['retries'])]
            actual_sleep_times = [call[0][0] for call in mock_sleep.call_args_list]
            assert actual_sleep_times == expected_sleep_times

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
            called_paths = {Path(call.args[0]).resolve() for call in mock_mkdir.call_args_list}
            expected_paths = {
                Path('/new/videos').resolve(),
                Path('/new/keyframes').resolve(),
            }
            assert expected_paths.issubset(called_paths)
            for call in mock_mkdir.call_args_list:
                assert call.kwargs == {'parents': True, 'exist_ok': True}
