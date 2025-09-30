"""Unit tests for VideoCleanupService."""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from datetime import datetime, timedelta

from services.cleanup_service import VideoCleanupService
from utils.file_cleanup import VideoCleanupManager


pytestmark = pytest.mark.unit


@pytest.fixture
async def cleanup_service_fixture():
    test_dir = tempfile.mkdtemp()

    # Create test files with different ages
    uploader1 = Path(test_dir) / "uploader1"
    uploader1.mkdir(parents=True)
    old_time = datetime.now() - timedelta(days=10)
    old_file = uploader1 / "old_video.mp4"
    old_file.write_text("old content")
    os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))

    # Persistently patch specific config attributes for this test case
    with patch.object(
        __import__('services.cleanup_service', fromlist=['config']).config,
        'VIDEO_RETENTION_DAYS', 7
    ), patch.object(
        __import__('services.cleanup_service', fromlist=['config']).config,
        'VIDEO_DIR', test_dir
    ), patch.object(
        __import__('services.cleanup_service', fromlist=['config']).config,
        'CLEANUP_OLD_VIDEOS', True
    ):
        cleanup_service = VideoCleanupService()
        yield cleanup_service, test_dir

    shutil.rmtree(test_dir, ignore_errors=True)


class TestVideoCleanupService:
    """Test cases for VideoCleanupService class"""

    def test_service_initialization(self, cleanup_service_fixture):
        """Test service initialization with enabled cleanup"""
        cleanup_service, _ = cleanup_service_fixture
        assert cleanup_service.enabled is True, "Cleanup should be enabled by default"
        assert isinstance(cleanup_service.cleanup_manager, VideoCleanupManager), \
            "Should have a cleanup manager instance"

    def test_service_initialization_disabled(self):
        """Test service initialization with disabled cleanup"""
        with patch.object(
            __import__('services.cleanup_service', fromlist=['config']).config,
            'CLEANUP_OLD_VIDEOS', False
        ):
            service = VideoCleanupService()
            assert service.enabled is False, "Cleanup should be disabled"

    @pytest.mark.asyncio
    async def test_perform_cleanup_enabled(self, cleanup_service_fixture):
        """Test cleanup when enabled"""
        cleanup_service, test_dir = cleanup_service_fixture
        results = await cleanup_service.perform_cleanup(test_dir, dry_run=False)

        # Should have performed cleanup
        assert results['enabled'] is True, "Cleanup should be enabled"
        assert len(results['files_removed']) == 1, "Should remove 1 file"
        assert results['total_files'] == 1, "Should have found 1 file to remove"
        assert results['total_size_freed'] > 0, "Should have freed space"

    @pytest.mark.asyncio
    async def test_perform_cleanup_disabled(self, cleanup_service_fixture):
        """Test cleanup when disabled"""
        cleanup_service, test_dir = cleanup_service_fixture
        cleanup_service.enabled = False

        results = await cleanup_service.perform_cleanup(test_dir, dry_run=False)

        # Should have skipped cleanup
        assert results['enabled'] is False, "Cleanup should be disabled"
        assert len(results['files_removed']) == 0, "Should remove no files"
        assert results['total_files'] == 0, "Should have found no files"

    @pytest.mark.asyncio
    async def test_perform_cleanup_dry_run(self, cleanup_service_fixture):
        """Test cleanup in dry run mode"""
        cleanup_service, test_dir = cleanup_service_fixture
        results = await cleanup_service.perform_cleanup(test_dir, dry_run=True)

        # Should be marked as dry run
        assert results['dry_run'] is True, "Should be marked as dry run"
        assert results['enabled'] is True, "Cleanup should still be enabled"
        assert len(results['files_skipped']) == 1, "Should have 1 file listed"
        assert len(results['files_removed']) == 0, "Should remove no files"

        # Files should still exist
        assert os.path.exists(test_dir), "Test directory should still exist"

    @pytest.mark.asyncio
    async def test_get_cleanup_info(self, cleanup_service_fixture):
        """Test getting cleanup information"""
        cleanup_service, test_dir = cleanup_service_fixture
        info = await cleanup_service.get_cleanup_info(test_dir)

        # Should return cleanup information
        assert 'total_old_files' in info, "Should have total old files count"
        assert 'total_size_bytes' in info, "Should have total size in bytes"
        assert 'total_size_mb' in info, "Should have total size in MB"
        assert 'retention_days' in info, "Should have retention days"
        assert 'cleanup_enabled' in info, "Should have cleanup enabled status"
        assert info['cleanup_enabled'] is True, "Cleanup should be enabled"

    @pytest.mark.asyncio
    async def test_get_cleanup_info_no_old_files(self, cleanup_service_fixture):
        """Test cleanup info when no old files exist"""
        cleanup_service, test_dir = cleanup_service_fixture
        # Remove old files
        shutil.rmtree(test_dir)
        os.makedirs(test_dir)

        info = await cleanup_service.get_cleanup_info(test_dir)

        assert info['total_old_files'] == 0, "Should find no old files"
        assert info['total_size_bytes'] == 0, "Should have 0 total size"
        assert info['oldest_file'] is None, "Should have no oldest file"
        assert info['newest_file'] is None, "Should have no newest file"

    @pytest.mark.asyncio
    async def test_enable_cleanup(self, cleanup_service_fixture):
        """Test enabling cleanup"""
        cleanup_service, _ = cleanup_service_fixture
        cleanup_service.enabled = False
        await cleanup_service.enable_cleanup(True)

        assert cleanup_service.enabled is True, "Cleanup should be enabled"

    @pytest.mark.asyncio
    async def test_disable_cleanup(self, cleanup_service_fixture):
        """Test disabling cleanup"""
        cleanup_service, _ = cleanup_service_fixture
        cleanup_service.enabled = True
        await cleanup_service.enable_cleanup(False)

        assert cleanup_service.enabled is False, "Cleanup should be disabled"

    def test_get_status(self, cleanup_service_fixture):
        """Test getting service status"""
        cleanup_service, test_dir = cleanup_service_fixture
        status = cleanup_service.get_status()

        # Should return status information
        assert 'enabled' in status, "Should have enabled status"
        assert 'retention_days' in status, "Should have retention days"
        assert 'video_dir' in status, "Should have video directory"

        assert status['enabled'] is True, "Cleanup should be enabled"
        assert status['retention_days'] == 7, "Should have 7 day retention"
        assert status['video_dir'] == test_dir, "Should have correct video directory"

    @patch('services.cleanup_service.logger')
    @pytest.mark.asyncio
    async def test_logging_enabled(self, mock_logger, cleanup_service_fixture):
        """Test logging when cleanup is enabled"""
        cleanup_service, test_dir = cleanup_service_fixture
        await cleanup_service.perform_cleanup(test_dir, dry_run=False)

        # Should log cleanup operations
        mock_logger.info.assert_called()

        # Check for cleanup start log
        cleanup_logs = [
            log_call
            for log_call in mock_logger.info.call_args_list
            if any(message in log_call.args[0] for message in ['CLEANUP-START', 'CLEANUP-COMPLETE'])
        ]
        assert len(cleanup_logs) > 0, "Should log cleanup operations"

    @patch('services.cleanup_service.logger')
    @pytest.mark.asyncio
    async def test_logging_disabled(self, mock_logger, cleanup_service_fixture):
        """Test logging when cleanup is disabled"""
        cleanup_service, test_dir = cleanup_service_fixture
        cleanup_service.enabled = False
        await cleanup_service.perform_cleanup(test_dir, dry_run=False)

        # Should log that cleanup is skipped
        mock_logger.info.assert_called()

        # Check for cleanup skipped log
        skip_logs = [
            log_call
            for log_call in mock_logger.info.call_args_list
            if 'CLEANUP-SKIPPED' in log_call.args[0]
        ]
        assert len(skip_logs) > 0, "Should log cleanup skipped"

    @pytest.mark.asyncio
    async def test_cleanup_error_handling(self, cleanup_service_fixture):
        """Test error handling during cleanup"""
        cleanup_service, _ = cleanup_service_fixture
        # Test with invalid directory
        invalid_dir = "/nonexistent/directory"
        results = await cleanup_service.perform_cleanup(invalid_dir, dry_run=False)

        # Should handle error gracefully and still return results
        assert isinstance(results, dict), "Should return results dict"
        assert results['enabled'] is False, "Cleanup should handle errors gracefully"

    @pytest.mark.asyncio
    async def test_cleanup_info_error_handling(self, cleanup_service_fixture):
        """Test error handling during cleanup info retrieval"""
        cleanup_service, _ = cleanup_service_fixture
        # Test with invalid directory
        invalid_dir = "/nonexistent/directory"

        # Should raise an exception or handle gracefully
        try:
            await cleanup_service.get_cleanup_info(invalid_dir)
        except Exception as e:
            # If it raises an exception, that's acceptable behavior
            assert str(e) in ['Path does not exist', 'No such file or directory']

    def test_video_cleanup_manager_instantiation(self):
        """Test that VideoCleanupManager is properly instantiated"""
        with patch.object(
            __import__('services.cleanup_service', fromlist=['config']).config,
            'VIDEO_RETENTION_DAYS', 10
        ):
            service = VideoCleanupService()
            # Cleanup manager should use configured retention days
            assert service.cleanup_manager.retention_days == 10
