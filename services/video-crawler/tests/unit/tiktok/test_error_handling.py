import asyncio

import pytest
from unittest.mock import Mock, patch
from platform_crawler.tiktok.tiktok_downloader import TikTokDownloader, TikTokAntiBotError


class TestErrorHandling:
    """Test error handling for TikTokDownloader"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            'TIKTOK_VIDEO_STORAGE_PATH': '/tmp/test_videos',
            'TIKTOK_KEYFRAME_STORAGE_PATH': '/tmp/test_keyframes',
            'retries': 3,
            'timeout': 30
        }
        self.downloader = TikTokDownloader(self.config)

    def test_anti_bot_detection_raises_tiktok_antibot_error(self):
        """Test that anti-bot detection raises TikTokAntiBotError"""
        with patch('yt_dlp.YoutubeDL') as mock_ydl, \
                patch('time.sleep') as mock_sleep:

            # Mock yt_dlp to raise anti-bot error indicators
            mock_ydl_instance = Mock()
            mock_ydl.return_value.__enter__.return_value = mock_ydl_instance

            anti_bot_errors = [
                "unable to extract",
                "HTTP Error 403: Forbidden",
                "HTTP Error 429: Too Many Requests",
                "rate limit exceeded",
                "access denied"
            ]

            for error_msg in anti_bot_errors:
                # Reset mocks
                mock_ydl_instance.download.side_effect = Exception(error_msg)
                mock_sleep.reset_mock()

                # Should raise TikTokAntiBotError
                with pytest.raises(TikTokAntiBotError) as exc_info:
                    self.downloader.download_video("https://example.com/video", "test_id")

                assert f"Anti-bot measures blocked download for {error_msg}" in str(exc_info.value)
                assert error_msg.lower() in str(exc_info.value).lower()

    def test_anti_bot_detection_with_retries(self):
        """Test that anti-bot detection retries with exponential backoff"""
        with patch('yt_dlp.YoutubeDL') as mock_ydl, \
                patch('time.sleep') as mock_sleep:

            # Mock yt_dlp to always raise anti-bot error
            mock_ydl_instance = Mock()
            mock_ydl.return_value.__enter__.return_value = mock_ydl_instance
            mock_ydl_instance.download.side_effect = Exception("HTTP Error 403: Forbidden")

            # Should raise TikTokAntiBotError after retries
            with pytest.raises(TikTokAntiBotError):
                self.downloader.download_video("https://example.com/video", "test_id")

            # Verify exponential backoff was used
            assert mock_sleep.call_count == self.config['retries']
            expected_sleep_times = [2**i for i in range(self.config['retries'])]
            actual_sleep_times = [call[0][0] for call in mock_sleep.call_args_list]
            assert actual_sleep_times == expected_sleep_times

    def test_general_exception_handling(self):
        """Test handling of general exceptions during download"""
        with patch('yt_dlp.YoutubeDL') as mock_ydl, \
                patch('time.sleep') as mock_sleep:

            # Mock yt_dlp to raise a general exception
            mock_ydl_instance = Mock()
            mock_ydl.return_value.__enter__.return_value = mock_ydl_instance
            mock_ydl_instance.download.side_effect = Exception("General network error")

            result = self.downloader.download_video("https://example.com/video", "test_id")

            # Should return None after all retries
            assert result is None

            # Verify retries were attempted
            assert mock_sleep.call_count == self.config['retries']

    def test_orchestrate_anti_bot_error(self):
        """Test that orchestration handles TikTokAntiBotError properly"""
        with patch.object(self.downloader, 'download_video') as mock_download:
            # Mock download to raise TikTokAntiBotError
            mock_download.side_effect = TikTokAntiBotError("Anti-bot detected")

            result = asyncio.run(
                self.downloader.orchestrate_download_and_extract(
                    "https://example.com/video", "test_id"
                )
            )

            # Should return False
            assert result is False

    def test_orchestrate_general_exception(self):
        """Test that orchestration handles general exceptions properly"""
        with patch.object(self.downloader, 'download_video') as mock_download:
            # Mock download to raise a general exception
            mock_download.side_effect = Exception("Unexpected error")

            result = asyncio.run(
                self.downloader.orchestrate_download_and_extract(
                    "https://example.com/video", "test_id"
                )
            )

            # Should return False
            assert result is False

    def test_extract_keyframes_exception(self):
        """Test exception handling during keyframe extraction"""
        with patch('os.path.join') as mock_join, \
                patch('keyframe_extractor.factory.KeyframeExtractorFactory.build'):

            # Mock keyframes directory creation to raise exception
            mock_join.side_effect = Exception("File system error")

            directory, frames = asyncio.run(
                self.downloader.extract_keyframes("/fake/path.mp4", "test_id")
            )

            # Should return empty result tuple
            assert directory is None
            assert frames == []

    def test_orchestrate_database_exception(self):
        """Test that orchestration handles database exceptions gracefully"""
        with patch.object(self.downloader, 'download_video') as mock_download, \
                patch.object(self.downloader, 'extract_keyframes') as mock_extract, \
                patch('libs.common_py.common_py.crud.video_frame_crud.VideoFrameCRUD') as mock_crud:

            # Mock successful download and extraction
            mock_download.return_value = "/fake/video.mp4"
            mock_extract.return_value = ("/fake/keyframes", [(0.0, '/fake/keyframes/frame_0.jpg')])

            # Mock database to raise exception
            mock_crud_instance = Mock()
            mock_crud.return_value = mock_crud_instance
            mock_crud_instance.create_video_frame.side_effect = Exception("Database error")

            # Mock database connection
            mock_db = Mock()

            # Should still return True despite database error
            result = asyncio.run(
                self.downloader.orchestrate_download_and_extract(
                    "https://example.com/video", "test_id", db=mock_db
                )
            )

            # Should succeed despite database error
            assert result is True

    def test_timeout_error_handling(self):
        """Test timeout error handling"""
        with patch('yt_dlp.YoutubeDL') as mock_ydl, \
                patch('time.sleep') as mock_sleep:

            # Mock yt_dlp to raise timeout error
            mock_ydl_instance = Mock()
            mock_ydl.return_value.__enter__.return_value = mock_ydl_instance
            mock_ydl_instance.download.side_effect = Exception("timeout exceeded")

            result = self.downloader.download_video("https://example.com/video", "test_id")

            # Should return None after retries
            assert result is None

            # Verify retries were attempted
            assert mock_sleep.call_count == self.config['retries']

    def test_connection_error_handling(self):
        """Test connection error handling"""
        with patch('yt_dlp.YoutubeDL') as mock_ydl, \
                patch('time.sleep') as mock_sleep:

            # Mock yt_dlp to raise connection error
            mock_ydl_instance = Mock()
            mock_ydl.return_value.__enter__.return_value = mock_ydl_instance
            mock_ydl_instance.download.side_effect = Exception("connection reset")

            result = self.downloader.download_video("https://example.com/video", "test_id")

            # Should return None after retries
            assert result is None

            # Verify retries were attempted
            assert mock_sleep.call_count == self.config['retries']

    def test_file_permission_error_handling(self):
        """Test file permission error handling"""
        with patch('yt_dlp.YoutubeDL') as mock_ydl, \
                patch('time.sleep') as mock_sleep:

            # Mock yt_dlp to raise permission error
            mock_ydl_instance = Mock()
            mock_ydl.return_value.__enter__.return_value = mock_ydl_instance
            mock_ydl_instance.download.side_effect = Exception("permission denied")

            result = self.downloader.download_video("https://example.com/video", "test_id")

            # Should return None after retries
            assert result is None

            # Verify retries were attempted
            assert mock_sleep.call_count == self.config['retries']

    def test_empty_config_error_handling(self):
        """Test error handling with empty configuration"""
        # Should not raise exception with empty config
        downloader = TikTokDownloader({})
        assert downloader is not None
        assert downloader.retries == 3  # default value
        assert downloader.timeout == 30  # default value

    def test_invalid_url_error_handling(self):
        """Test error handling with invalid URL"""
        with patch('yt_dlp.YoutubeDL') as mock_ydl, \
                patch('time.sleep') as mock_sleep:

            # Mock yt_dlp to fail on invalid URL
            mock_ydl_instance = Mock()
            mock_ydl.return_value.__enter__.return_value = mock_ydl_instance
            mock_ydl_instance.download.side_effect = Exception("invalid URL")

            result = self.downloader.download_video("invalid-url", "test_id")

            # Should return None after retries
            assert result is None

            # Verify retries were attempted
            assert mock_sleep.call_count == self.config['retries']
