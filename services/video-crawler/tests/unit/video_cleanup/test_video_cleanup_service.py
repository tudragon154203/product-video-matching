"""
Unit tests for VideoCleanupService
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from services.cleanup_service import VideoCleanupService
from utils.file_cleanup import VideoCleanupManager


class TestVideoCleanupService(unittest.TestCase):
    """Test cases for VideoCleanupService class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.create_test_files()
        
        # Persistently patch specific config attributes for this test case
        self.patcher_retention = patch.object(
            __import__('services.cleanup_service', fromlist=['config']).config,
            'VIDEO_RETENTION_DAYS', 7
        )
        self.patcher_video_dir = patch.object(
            __import__('services.cleanup_service', fromlist=['config']).config,
            'VIDEO_DIR', self.test_dir
        )
        self.patcher_enable = patch.object(
            __import__('services.cleanup_service', fromlist=['config']).config,
            'CLEANUP_OLD_VIDEOS', True
        )
        self.patcher_retention.start()
        self.patcher_video_dir.start()
        self.patcher_enable.start()
        self.addCleanup(self.patcher_retention.stop)
        self.addCleanup(self.patcher_video_dir.stop)
        self.addCleanup(self.patcher_enable.stop)
        
        self.cleanup_service = VideoCleanupService()
            
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def create_test_files(self):
        """Create test files with different ages"""
        from datetime import datetime, timedelta
        
        # Create uploader directories
        uploader1 = Path(self.test_dir) / "uploader1"
        uploader1.mkdir(parents=True)
        
        # Create an old file (10 days old)
        old_time = datetime.now() - timedelta(days=10)
        old_file = uploader1 / "old_video.mp4"
        old_file.write_text("old content")
        os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))
        
    def test_service_initialization(self):
        """Test service initialization with enabled cleanup"""
        self.assertTrue(self.cleanup_service.enabled, "Cleanup should be enabled by default")
        self.assertIsInstance(self.cleanup_service.cleanup_manager, VideoCleanupManager, 
                            "Should have a cleanup manager instance")
        
    def test_service_initialization_disabled(self):
        """Test service initialization with disabled cleanup"""
        with patch.object(
            __import__('services.cleanup_service', fromlist=['config']).config,
            'CLEANUP_OLD_VIDEOS', False
        ):
            service = VideoCleanupService()
            self.assertFalse(service.enabled, "Cleanup should be disabled")
            
    async def test_perform_cleanup_enabled(self):
        """Test cleanup when enabled"""
        results = await self.cleanup_service.perform_cleanup(self.test_dir, dry_run=False)
        
        # Should have performed cleanup
        self.assertTrue(results['enabled'], "Cleanup should be enabled")
        self.assertEqual(len(results['files_removed']), 1, "Should remove 1 file")
        self.assertEqual(results['total_files'], 1, "Should have found 1 file to remove")
        self.assertTrue(results['total_size_freed'] > 0, "Should have freed space")
        
    async def test_perform_cleanup_disabled(self):
        """Test cleanup when disabled"""
        self.cleanup_service.enabled = False
        
        results = await self.cleanup_service.perform_cleanup(self.test_dir, dry_run=False)
        
        # Should have skipped cleanup
        self.assertFalse(results['enabled'], "Cleanup should be disabled")
        self.assertEqual(len(results['files_removed']), 0, "Should remove no files")
        self.assertEqual(results['total_files'], 0, "Should have found no files")
        
    async def test_perform_cleanup_dry_run(self):
        """Test cleanup in dry run mode"""
        results = await self.cleanup_service.perform_cleanup(self.test_dir, dry_run=True)
        
        # Should be marked as dry run
        self.assertTrue(results['dry_run'], "Should be marked as dry run")
        self.assertTrue(results['enabled'], "Cleanup should still be enabled")
        self.assertEqual(len(results['files_skipped']), 1, "Should have 1 file listed")
        self.assertEqual(len(results['files_removed']), 0, "Should remove no files")
        
        # Files should still exist
        self.assertTrue(os.path.exists(self.test_dir), "Test directory should still exist")
        
    async def test_get_cleanup_info(self):
        """Test getting cleanup information"""
        info = await self.cleanup_service.get_cleanup_info(self.test_dir)
        
        # Should return cleanup information
        self.assertIn('total_old_files', info, "Should have total old files count")
        self.assertIn('total_size_bytes', info, "Should have total size in bytes")
        self.assertIn('total_size_mb', info, "Should have total size in MB")
        self.assertIn('retention_days', info, "Should have retention days")
        self.assertIn('cleanup_enabled', info, "Should have cleanup enabled status")
        self.assertTrue(info['cleanup_enabled'], "Cleanup should be enabled")
        
    async def test_get_cleanup_info_no_old_files(self):
        """Test cleanup info when no old files exist"""
        # Remove old files
        import shutil
        shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
        info = await self.cleanup_service.get_cleanup_info(self.test_dir)
        
        self.assertEqual(info['total_old_files'], 0, "Should find no old files")
        self.assertEqual(info['total_size_bytes'], 0, "Should have 0 total size")
        self.assertIsNone(info['oldest_file'], "Should have no oldest file")
        self.assertIsNone(info['newest_file'], "Should have no newest file")
        
    async def test_enable_cleanup(self):
        """Test enabling cleanup"""
        self.cleanup_service.enabled = False
        await self.cleanup_service.enable_cleanup(True)
        
        self.assertTrue(self.cleanup_service.enabled, "Cleanup should be enabled")
        
    async def test_disable_cleanup(self):
        """Test disabling cleanup"""
        self.cleanup_service.enabled = True
        await self.cleanup_service.enable_cleanup(False)
        
        self.assertFalse(self.cleanup_service.enabled, "Cleanup should be disabled")
        
    def test_get_status(self):
        """Test getting service status"""
        status = self.cleanup_service.get_status()
        
        # Should return status information
        self.assertIn('enabled', status, "Should have enabled status")
        self.assertIn('retention_days', status, "Should have retention days")
        self.assertIn('video_dir', status, "Should have video directory")
        
        self.assertTrue(status['enabled'], "Cleanup should be enabled")
        self.assertEqual(status['retention_days'], 7, "Should have 7 day retention")
        self.assertEqual(status['video_dir'], self.test_dir, "Should have correct video directory")
        
    @patch('services.cleanup_service.logger')
    async def test_logging_enabled(self, mock_logger):
        """Test logging when cleanup is enabled"""
        await self.cleanup_service.perform_cleanup(self.test_dir, dry_run=False)
        
        # Should log cleanup operations
        mock_logger.info.assert_called()
        
        # Check for cleanup start log
        cleanup_logs = [call for call in mock_logger.info.call_args_list 
                       if any(x in call.args[0] for x in ['CLEANUP-START', 'CLEANUP-COMPLETE'])]
        self.assertTrue(len(cleanup_logs) > 0, "Should log cleanup operations")
        
    @patch('services.cleanup_service.logger')
    async def test_logging_disabled(self, mock_logger):
        """Test logging when cleanup is disabled"""
        self.cleanup_service.enabled = False
        await self.cleanup_service.perform_cleanup(self.test_dir, dry_run=False)
        
        # Should log that cleanup is skipped
        mock_logger.info.assert_called()
        
        # Check for cleanup skipped log
        skip_logs = [call for call in mock_logger.info.call_args_list 
                    if 'CLEANUP-SKIPPED' in call.args[0]]
        self.assertTrue(len(skip_logs) > 0, "Should log cleanup skipped")
        
    async def test_cleanup_error_handling(self):
        """Test error handling during cleanup"""
        # Test with invalid directory
        invalid_dir = "/nonexistent/directory"
        results = await self.cleanup_service.perform_cleanup(invalid_dir, dry_run=False)
        
        # Should handle error gracefully and still return results
        self.assertIsInstance(results, dict, "Should return results dict")
        self.assertFalse(results['enabled'], "Cleanup should handle errors gracefully")
        
    async def test_cleanup_info_error_handling(self):
        """Test error handling during cleanup info retrieval"""
        # Test with invalid directory
        invalid_dir = "/nonexistent/directory"
        
        # Should raise an exception or handle gracefully
        try:
            await self.cleanup_service.get_cleanup_info(invalid_dir)
        except Exception as e:
            # If it raises an exception, that's acceptable behavior
            self.assertIn(str(e), ['Path does not exist', 'No such file or directory'])

    def test_video_cleanup_manager_instantiation(self):
        """Test that VideoCleanupManager is properly instantiated"""
        with patch.object(
            __import__('services.cleanup_service', fromlist=['config']).config,
            'VIDEO_RETENTION_DAYS', 10
        ):
            service = VideoCleanupService()
            # Cleanup manager should use configured retention days
            self.assertEqual(service.cleanup_manager.retention_days, 10)


if __name__ == '__main__':
    unittest.main()
