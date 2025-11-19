import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from platform_crawler.tiktok.tiktok_downloader import TikTokDownloader


class TestScraplingApiStrategyIntegration:
    """Integration tests for the scrapling-api strategy."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            video_dir = os.path.join(temp_dir, "videos")
            keyframe_dir = os.path.join(temp_dir, "keyframes")
            os.makedirs(video_dir, exist_ok=True)
            os.makedirs(keyframe_dir, exist_ok=True)
            yield video_dir, keyframe_dir

    @pytest.fixture
    def config(self, temp_dirs):
        """Create test configuration."""
        video_dir, keyframe_dir = temp_dirs
        return {
            "TIKTOK_DOWNLOAD_STRATEGY": "scrapling-api",
            "TIKTOK_CRAWL_HOST": "localhost",
            "TIKTOK_CRAWL_HOST_PORT": "5680",
            "TIKTOK_DOWNLOAD_TIMEOUT": 30,
            "TIKTOK_VIDEO_STORAGE_PATH": video_dir,
            "TIKTOK_KEYFRAME_STORAGE_PATH": keyframe_dir,
            "retries": 1,
            "timeout": 30
        }

    @patch('platform_crawler.tiktok.download_strategies.scrapling_api_strategy.httpx.AsyncClient')
    @patch('platform_crawler.tiktok.tiktok_download_client.httpx.AsyncClient')
    def test_end_to_end_download_success(self, mock_api_client, mock_download_client, config, temp_dirs):
        """Test end-to-end successful download and keyframe extraction."""
        video_dir, keyframe_dir = temp_dirs
        video_id = "test_video_123"
        video_url = "https://www.tiktok.com/@testuser/video/1234567890"
        video_path = os.path.join(video_dir, f"{video_id}.mp4")

        # Mock API client response
        mock_api_response = MagicMock()
        mock_api_response.status_code = 200
        mock_api_response.raise_for_status = MagicMock()
        mock_api_response.json.return_value = {
            "status": "success",
            "message": "Video download URL resolved successfully",
            "download_url": "http://example.com/video.mp4",
            "video_info": {
                "id": video_id,
                "title": "Test Video",
                "author": "testuser",
                "duration": 30.5
            },
            "file_size": 1000000,
            "execution_time": 5.0
        }

        mock_api_session = AsyncMock()
        mock_api_session.post.return_value = mock_api_response
        mock_api_client.return_value.__aenter__.return_value = mock_api_session

        # Mock download client streaming
        mock_download_response = MagicMock()
        mock_download_response.headers = {"content-length": "1000000"}
        mock_download_response.raise_for_status = MagicMock()
        mock_download_response.aiter_bytes.return_value = [b'fake_video_data'] * 10

        mock_download_session = AsyncMock()
        mock_download_session.stream.return_value.__aenter__.return_value = mock_download_response
        mock_download_client.return_value.__aenter__.return_value = mock_download_session

        # Create downloader and test
        downloader = TikTokDownloader(config)

        # Test download_video
        result = downloader.download_video(video_url, video_id, video_dir)

        assert result is not None
        assert result == video_path

    @patch('platform_crawler.tiktok.download_strategies.scrapling_api_strategy.httpx.AsyncClient')
    @patch('platform_crawler.tiktok.tiktok_download_client.httpx.AsyncClient')
    def test_download_api_error_no_retry(self, mock_api_client, mock_download_client, config, temp_dirs):
        """Test download with API error that doesn't trigger retry."""
        video_dir, keyframe_dir = temp_dirs
        video_id = "test_video_456"
        video_url = "https://www.tiktok.com/@testuser/video/invalid"

        # Mock API client error response
        mock_api_response = MagicMock()
        mock_api_response.status_code = 200
        mock_api_response.raise_for_status = MagicMock()
        mock_api_response.json.return_value = {
            "status": "error",
            "message": "Invalid TikTok video URL format",
            "error_code": "INVALID_URL",
            "execution_time": 0.5
        }

        mock_api_session = AsyncMock()
        mock_api_session.post.return_value = mock_api_response
        mock_api_client.return_value.__aenter__.return_value = mock_api_session

        # Create downloader and test
        downloader = TikTokDownloader(config)

        # Test download_video
        result = downloader.download_video(video_url, video_id, video_dir)

        assert result is None

    @patch('platform_crawler.tiktok.download_strategies.scrapling_api_strategy.httpx.AsyncClient')
    @patch('platform_crawler.tiktok.tiktok_download_client.httpx.AsyncClient')
    def test_download_api_error_with_retry_success(self, mock_api_client, mock_download_client, config, temp_dirs):
        """Test download that fails headless but succeeds headful."""
        video_dir, keyframe_dir = temp_dirs
        video_id = "test_video_789"
        video_url = "https://www.tiktok.com/@testuser/video/7890123456"
        video_path = os.path.join(video_dir, f"{video_id}.mp4")

        call_count = 0

        # Mock API client response
        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()

            if call_count == 1:  # First call (headless) fails
                mock_response.json.return_value = {
                    "status": "error",
                    "message": "Browser navigation failed",
                    "error_code": "NAVIGATION_FAILED",
                    "execution_time": 8.0
                }
            else:  # Second call (headful) succeeds
                mock_response.json.return_value = {
                    "status": "success",
                    "message": "Video download URL resolved successfully",
                    "download_url": "http://example.com/video.mp4",
                    "video_info": {
                        "id": video_id,
                        "title": "Test Video",
                        "author": "testuser",
                        "duration": 30.5
                    },
                    "file_size": 1000000,
                    "execution_time": 12.0
                }

            return mock_response

        mock_api_session = AsyncMock()
        mock_api_session.post.side_effect = mock_post
        mock_api_client.return_value.__aenter__.return_value = mock_api_session

        # Mock download client streaming
        mock_download_response = MagicMock()
        mock_download_response.headers = {"content-length": "1000000"}
        mock_download_response.raise_for_status = MagicMock()
        mock_download_response.aiter_bytes.return_value = [b'fake_video_data'] * 10

        mock_download_session = AsyncMock()
        mock_download_session.stream.return_value.__aenter__.return_value = mock_download_response
        mock_download_client.return_value.__aenter__.return_value = mock_download_session

        # Create downloader and test
        downloader = TikTokDownloader(config)

        # Test download_video
        result = downloader.download_video(video_url, video_id, video_dir)

        assert result is not None
        assert result == video_path
        assert call_count == 2  # Should be called twice for retry

    @patch('platform_crawler.tiktok.download_strategies.scrapling_api_strategy.httpx.AsyncClient')
    @patch('platform_crawler.tiktok.tiktok_download_client.httpx.AsyncClient')
    def test_download_file_too_large(self, mock_api_client, mock_download_client, config, temp_dirs):
        """Test download when file exceeds size limit."""
        video_dir, keyframe_dir = temp_dirs
        video_id = "test_video_large"
        video_url = "https://www.tiktok.com/@testuser/video/large"

        # Mock API client response
        mock_api_response = MagicMock()
        mock_api_response.status_code = 200
        mock_api_response.raise_for_status = MagicMock()
        mock_api_response.json.return_value = {
            "status": "success",
            "message": "Video download URL resolved successfully",
            "download_url": "http://example.com/large_video.mp4",
            "video_info": {
                "id": video_id,
                "title": "Large Video",
                "author": "testuser",
                "duration": 300.0
            },
            "file_size": 600 * 1024 * 1024,  # 600MB - exceeds limit
            "execution_time": 5.0
        }

        mock_api_session = AsyncMock()
        mock_api_session.post.return_value = mock_api_response
        mock_api_client.return_value.__aenter__.return_value = mock_api_session

        # Mock download client streaming with large file size in headers
        mock_download_response = MagicMock()
        mock_download_response.headers = {"content-length": str(600 * 1024 * 1024)}
        mock_download_response.raise_for_status = MagicMock()

        mock_download_session = AsyncMock()
        mock_download_session.stream.return_value.__aenter__.return_value = mock_download_response
        mock_download_client.return_value.__aenter__.return_value = mock_download_session

        # Create downloader and test
        downloader = TikTokDownloader(config)

        # Test download_video
        result = downloader.download_video(video_url, video_id, video_dir)

        assert result is None

    @patch('platform_crawler.tiktok.download_strategies.scrapling_api_strategy.httpx.AsyncClient')
    @patch('platform_crawler.tiktok.tiktok_download_client.httpx.AsyncClient')
    def test_orchestrate_download_and_extract_success(self, mock_api_client, mock_download_client, config, temp_dirs):
        """Test complete orchestration of download and keyframe extraction."""
        video_dir, keyframe_dir = temp_dirs
        video_id = "test_video_orchestrate"
        video_url = "https://www.tiktok.com/@testuser/video/orchestrate"
        video_path = os.path.join(video_dir, f"{video_id}.mp4")

        # Mock API client response
        mock_api_response = MagicMock()
        mock_api_response.status_code = 200
        mock_api_response.raise_for_status = MagicMock()
        mock_api_response.json.return_value = {
            "status": "success",
            "message": "Video download URL resolved successfully",
            "download_url": "http://example.com/video.mp4",
            "video_info": {
                "id": video_id,
                "title": "Orchestration Test",
                "author": "testuser",
                "duration": 30.5
            },
            "file_size": 1000000,
            "execution_time": 5.0
        }

        mock_api_session = AsyncMock()
        mock_api_session.post.return_value = mock_api_response
        mock_api_client.return_value.__aenter__.return_value = mock_api_session

        # Mock download client streaming
        mock_download_response = MagicMock()
        mock_download_response.headers = {"content-length": "1000000"}
        mock_download_response.raise_for_status = MagicMock()
        mock_download_response.aiter_bytes.return_value = [b'fake_video_data'] * 10

        mock_download_session = AsyncMock()
        mock_download_session.stream.return_value.__aenter__.return_value = mock_download_response
        mock_download_client.return_value.__aenter__.return_value = mock_download_session

        # Create a fake video file for keyframe extraction
        Path(video_path).parent.mkdir(parents=True, exist_ok=True)
        with open(video_path, 'wb') as f:
            f.write(b'fake_video_content')

        # Mock keyframe extraction
        with patch(
            'platform_crawler.tiktok.download_strategies.scrapling_api_strategy.LengthAdaptiveKeyframeExtractor'
        ) as mock_extractor_class:
            mock_extractor = MagicMock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.extract_keyframes.return_value = [
                (1.0, f"{video_dir}/keyframes/{video_id}/frame_1.jpg"),
                (2.0, f"{video_dir}/keyframes/{video_id}/frame_2.jpg"),
            ]

            # Create downloader and test
            downloader = TikTokDownloader(config)

            # Test orchestrate_download_and_extract
            success = downloader.download_videos_batch({
                video_id: {
                    "id": video_id,
                    "webViewUrl": video_url,
                    "caption": "Test video"
                }
            }, video_dir, max_parallel_downloads=1)

            assert len(success) == 1
            assert success[0]["local_path"] == video_path
            assert success[0]["video_id"] == video_id

    def test_strategy_factory_creates_scrapling_strategy(self, config):
        """Test that factory correctly creates scrapling-api strategy."""
        downloader = TikTokDownloader(config)

        # The strategy should be scrapling-api based on config
        assert hasattr(downloader.download_strategy, 'api_host')
        assert hasattr(downloader.download_strategy, 'api_port')
        assert hasattr(downloader.download_strategy, 'api_timeout')

    def test_default_strategy_tikwm(self, temp_dirs):
        """Test that tikwm is the default strategy."""
        video_dir, keyframe_dir = temp_dirs
        config_without_strategy = {
            "TIKTOK_VIDEO_STORAGE_PATH": video_dir,
            "TIKTOK_KEYFRAME_STORAGE_PATH": keyframe_dir,
            "retries": 1,
            "timeout": 30
        }

        # Clear environment variable to ensure default behavior
        with patch.dict(os.environ, {}, clear=True):
            downloader = TikTokDownloader(config_without_strategy)

            # Should default to tikwm strategy
            assert type(downloader.download_strategy).__name__ == "TikwmDownloadStrategy"
