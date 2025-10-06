"""Unit tests for VideoCleanupService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.video_cleanup_service import VideoCleanupService
from services.exceptions import CleanupOperationError

pytestmark = pytest.mark.unit


class TestVideoCleanupService:
    """Tests for VideoCleanupService class."""

    def test_video_cleanup_service_initialization(self):
        """Test VideoCleanupService initialization."""
        service = VideoCleanupService()
        assert service._video_dir_override is None

    def test_video_cleanup_service_initialization_with_override(self):
        """Test VideoCleanupService initialization with directory override."""
        service = VideoCleanupService(video_dir_override="/custom/path")
        assert service._video_dir_override == "/custom/path"

    @pytest.mark.asyncio
    async def test_run_auto_cleanup_enabled(self):
        """Test running automatic cleanup when enabled."""
        service = VideoCleanupService()
        job_id = "test_job_123"

        with patch('services.video_cleanup_service.config') as mock_config:
            mock_config.CLEANUP_OLD_VIDEOS = True

            with patch('services.video_cleanup_service.cleanup_service') as mock_cleanup:
                mock_cleanup.perform_cleanup = AsyncMock(return_value={'files_removed': ['file1', 'file2']})

                # Should not raise exception
                await service.run_auto_cleanup(job_id)

                mock_cleanup.perform_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_auto_cleanup_disabled(self):
        """Test running automatic cleanup when disabled."""
        service = VideoCleanupService()
        job_id = "test_job_123"

        with patch('services.video_cleanup_service.config') as mock_config:
            mock_config.CLEANUP_OLD_VIDEOS = False

            with patch('services.video_cleanup_service.cleanup_service') as mock_cleanup:
                mock_cleanup.perform_cleanup = AsyncMock()

                # Should not raise exception
                await service.run_auto_cleanup(job_id)

                # Cleanup should not be called
                mock_cleanup.perform_cleanup.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_auto_cleanup_with_exception(self):
        """Test running automatic cleanup with exception handling."""
        service = VideoCleanupService()
        job_id = "test_job_123"

        with patch('services.video_cleanup_service.config') as mock_config:
            mock_config.CLEANUP_OLD_VIDEOS = True

            with patch('services.video_cleanup_service.cleanup_service') as mock_cleanup:
                mock_cleanup.perform_cleanup = AsyncMock(side_effect=Exception("Cleanup error"))

                # Should not raise exception
                await service.run_auto_cleanup(job_id)

                mock_cleanup.perform_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_manual_cleanup_dry_run(self):
        """Test running manual cleanup with dry run."""
        service = VideoCleanupService()

        with patch('services.video_cleanup_service.cleanup_service') as mock_cleanup:
            mock_cleanup.get_cleanup_info = AsyncMock(return_value={'old_files': ['file1']})
            mock_cleanup.perform_cleanup = AsyncMock(return_value={'files_removed': []})

            result = await service.run_manual_cleanup(dry_run=True)

            assert 'cleanup_info' in result
            assert 'cleanup_results' in result
            assert 'config' in result
            mock_cleanup.perform_cleanup.assert_called_once_with(service._get_video_dir(), True)

    @pytest.mark.asyncio
    async def test_run_manual_cleanup_actual_cleanup(self):
        """Test running manual cleanup with actual cleanup."""
        service = VideoCleanupService()

        with patch('services.video_cleanup_service.cleanup_service') as mock_cleanup:
            mock_cleanup.get_cleanup_info = AsyncMock(return_value={'old_files': ['file1']})
            mock_cleanup.perform_cleanup = AsyncMock(return_value={'files_removed': ['file1']})

            result = await service.run_manual_cleanup(dry_run=False)

            assert 'cleanup_info' in result
            assert 'cleanup_results' in result
            assert 'config' in result
            mock_cleanup.perform_cleanup.assert_called_once_with(service._get_video_dir(), False)

    @pytest.mark.asyncio
    async def test_run_manual_cleanup_with_exception(self):
        """Test running manual cleanup with exception."""
        service = VideoCleanupService()

        with patch('services.video_cleanup_service.cleanup_service') as mock_cleanup:
            mock_cleanup.get_cleanup_info = AsyncMock(side_effect=Exception("Info error"))
            mock_cleanup.perform_cleanup = AsyncMock()

            with pytest.raises(Exception, match="Info error"):
                await service.run_manual_cleanup()

    def test_get_video_dir_default(self):
        """Test getting video directory with default config."""
        service = VideoCleanupService()

        with patch('services.video_cleanup_service.config') as mock_config:
            mock_config.VIDEO_DIR = "/default/video/dir"

            result = service._get_video_dir()

            assert result == "/default/video/dir"

    def test_get_video_dir_with_override(self):
        """Test getting video directory with override."""
        service = VideoCleanupService(video_dir_override="/override/path")

        result = service._get_video_dir()

        assert result == "/override/path"

    def test_get_cleanup_status_enabled(self):
        """Test getting cleanup status when enabled."""
        service = VideoCleanupService()

        with patch('services.video_cleanup_service.config') as mock_config:
            mock_config.CLEANUP_OLD_VIDEOS = True
            mock_config.VIDEO_RETENTION_DAYS = 7

            with patch('services.video_cleanup_service.cleanup_service') as mock_cleanup:
                mock_cleanup.get_status.return_value = {'status': 'active'}

                result = service.get_cleanup_status()

                assert result['enabled'] is True
                assert result['retention_days'] == 7
                assert result['video_dir'] == service._get_video_dir()
                assert result['service_status']['status'] == 'active'

    def test_get_cleanup_status_disabled(self):
        """Test getting cleanup status when disabled."""
        service = VideoCleanupService()

        with patch('services.video_cleanup_service.config') as mock_config:
            mock_config.CLEANUP_OLD_VIDEOS = False
            mock_config.VIDEO_RETENTION_DAYS = 30

            with patch('services.video_cleanup_service.cleanup_service') as mock_cleanup:
                mock_cleanup.get_status.return_value = {'status': 'inactive'}

                result = service.get_cleanup_status()

                assert result['enabled'] is False
                assert result['retention_days'] == 30
                assert result['video_dir'] == service._get_video_dir()
                assert result['service_status']['status'] == 'inactive'