"""
Integration tests for video cleanup workflow
"""

import os
import tempfile
import unittest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, AsyncMock

from services.service import VideoCrawlerService
from services.cleanup_service import VideoCleanupService
from config_loader import config


class TestCleanupIntegration(unittest.TestCase):
    """Integration tests for cleanup workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.create_test_video_files()
        
        # Mock config for cleanup testing
        self.original_config = {
            'VIDEO_DIR': self.test_dir,
            'CLEANUP_OLD_VIDEOS': True,
            'VIDEO_RETENTION_DAYS': 7
        }
        
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def create_test_video_files(self):
        """Create test video files simulate realistic scenario"""
        # Create uploader directories
        uploaders = ['channel1', 'channel2', 'channel3']
        self.uploader_dirs = {}
        
        for uploader in uploaders:
            uploader_dir = Path(self.test_dir) / uploader
            uploader_dir.mkdir()
            self.uploader_dirs[uploader] = uploader_dir
            
            # Create files with different ages
            now = datetime.now()
            
            # Recent files (3-5 days old) - should NOT be cleaned up
            for i in range(2):
                recent_time = now - timedelta(days=3 + i)
                recent_file = uploader_dir / f"recent_video_{i}.mp4"
                recent_file.write_text(f"recent video {i} content")
                os.utime(recent_file, (recent_time.timestamp(), recent_time.timestamp()))
                
            # Old files (10-15 days old) - SHOULD be cleaned up
            for i in range(2):
                old_time = now - timedelta(days=10 + i)
                old_file = uploader_dir / f"old_video_{i}.mp4"
                old_file.write_text(f"old video {i} content")
                os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))
                
        # Keep track of expected files
        self.recent_files = []
        self.old_files = []
        
        for uploader in uploaders:
            uploader_dir = self.uploader_dirs[uploader]
            
            # Get recent files
            for file in uploader_dir.glob("recent*.mp4"):
                self.recent_files.append(str(file))
                
            # Get old files  
            for file in uploader_dir.glob("old*.mp4"):
                self.old_files.append(str(file))
                
    def test_cleanup_workflow_with_service_integration(self):
        """Test integrated cleanup with service layer"""
        with patch.object(config, 'VIDEO_DIR', self.test_dir), \
             patch.object(config, 'CLEANUP_OLD_VIDEOS', True), \
             patch.object(config, 'VIDEO_RETENTION_DAYS', 7):
            cleanup_service = VideoCleanupService()
            
            # Run actual cleanup
            async def run_cleanup():
                return await cleanup_service.perform_cleanup(self.test_dir, dry_run=False)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(run_cleanup())
            finally:
                loop.close()
                
            # Verify cleanup results
            self.assertEqual(len(results['files_removed']), len(self.old_files), 
                            f"Should remove {len(self.old_files)} old files")
            self.assertEqual(len(results['files_skipped']), 0, "Should skip no files")
            self.assertEqual(results['total_files'], len(self.old_files), "Should find correct number of files to remove")
            self.assertTrue(results['total_size_freed'] > 0, "Should have freed space")
            
            # Verify files were actually removed
            for old_file in self.old_files:
                self.assertFalse(os.path.exists(old_file), f"Old file {old_file} should be removed")
                
            # Verify recent files still exist
            for recent_file in self.recent_files:
                self.assertTrue(os.path.exists(recent_file), f"Recent file {recent_file} should still exist")
                
    def test_cleanup_workflow_dry_run(self):
        """Test cleanup workflow in dry run mode"""
        with patch.object(config, 'VIDEO_DIR', self.test_dir), \
             patch.object(config, 'CLEANUP_OLD_VIDEOS', True), \
             patch.object(config, 'VIDEO_RETENTION_DAYS', 7):
            cleanup_service = VideoCleanupService()
            
            # Run dry run
            async def run_dry_run():
                return await cleanup_service.perform_cleanup(self.test_dir, dry_run=True)
                
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(run_dry_run())
            finally:
                loop.close()
                
            # Verify dry run results
            self.assertEqual(len(results['files_skipped']), len(self.old_files), 
                            f"Should list {len(self.old_files)} old files")
            self.assertEqual(len(results['files_removed']), 0, "Should remove no files in dry run")
            self.assertTrue(results['dry_run'], "Should be marked as dry run")
            
            # Verify files still exist
            for old_file in self.old_files:
                self.assertTrue(os.path.exists(old_file), f"Old file {old_file} should still exist after dry run")
                
    def test_cleanup_info_integration(self):
        """Test getting cleanup information"""
        with patch.object(config, 'VIDEO_DIR', self.test_dir), \
             patch.object(config, 'CLEANUP_OLD_VIDEOS', True), \
             patch.object(config, 'VIDEO_RETENTION_DAYS', 7):
            cleanup_service = VideoCleanupService()
            
            # Get cleanup info
            async def get_info():
                return await cleanup_service.get_cleanup_info(self.test_dir)
                
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                info = loop.run_until_complete(get_info())
            finally:
                loop.close()
                
            # Verify cleanup info
            self.assertEqual(info['total_old_files'], len(self.old_files), "Should have correct count of old files")
            self.assertTrue(info['total_size_bytes'] > 0, "Should have positive total size")
            self.assertEqual(info['retention_days'], 7, "Should have correct retention days")
            self.assertTrue(info['cleanup_enabled'], "Cleanup should be enabled")
            self.assertIsNotNone(info['oldest_file'], "Should have oldest file info")
            self.assertIsNotNone(info['newest_file'], "Should have newest file info")
            
    def test_cleanup_service_control(self):
        """Test enabling and disabling cleanup service"""
        with patch.object(config, 'VIDEO_DIR', self.test_dir), \
             patch.object(config, 'CLEANUP_OLD_VIDEOS', True), \
             patch.object(config, 'VIDEO_RETENTION_DAYS', 7):
            cleanup_service = VideoCleanupService()
            
            # Initially enabled
            self.assertTrue(cleanup_service.enabled, "Cleanup should be initially enabled")
            
            # Disable cleanup
            async def disable():
                await cleanup_service.enable_cleanup(False)
                return cleanup_service.enabled
                
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                disabled = loop.run_until_complete(disable())
            finally:
                loop.close()
                
            self.assertFalse(disabled, "Cleanup should be disabled")
            
            # Try cleanup when disabled
            async def cleanup_disabled():
                return await cleanup_service.perform_cleanup(self.test_dir, dry_run=False)
                
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(cleanup_disabled())
            finally:
                loop.close()
                
            self.assertFalse(results['enabled'], "Cleanup should be disabled")
            self.assertEqual(len(results['files_removed']), 0, "Should remove no files when disabled")
            
            # Re-enable cleanup
            async def reenable():
                await cleanup_service.enable_cleanup(True)
                return cleanup_service.enabled
                
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                enabled = loop.run_until_complete(reenable())
            finally:
                loop.close()
                
            self.assertTrue(enabled, "Cleanup should be re-enabled")
            
    def test_directory_cleanup_integration(self):
        """Test empty directory cleanup integration"""
        with patch.object(config, 'VIDEO_DIR', self.test_dir), \
             patch.object(config, 'CLEANUP_OLD_VIDEOS', True), \
             patch.object(config, 'VIDEO_RETENTION_DAYS', 7):
            cleanup_service = VideoCleanupService()
            
            # Remove some files to create empty directories
            for uploader, uploader_dir in self.uploader_dirs.items():
                # Keep one file, remove others to create empty directories
                files = list(uploader_dir.glob("*.mp4"))
                if len(files) > 1:
                    for file in files[1:]:
                        file.unlink()
                        
            # Run cleanup (this should leave some empty directories)
            async def run_cleanup():
                # First clean up files
                await cleanup_service.perform_cleanup(self.test_dir, dry_run=False)
                # Then clean up empty directories
                results = cleanup_service.cleanup_manager.cleanup_empty_directories(self.test_dir, dry_run=False)
                return results
                
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(run_cleanup())
            finally:
                loop.close()
                
            self.assertIsInstance(results, list, "Should return list of removed directories")
            # Some directories should have been removed if they became empty
            
    def test_cleanup_status_reporting(self):
        """Test cleanup status reporting integration"""
        with patch.object(config, 'VIDEO_DIR', self.test_dir), \
             patch.object(config, 'CLEANUP_OLD_VIDEOS', True), \
             patch.object(config, 'VIDEO_RETENTION_DAYS', 7):
            cleanup_service = VideoCleanupService()
            
            status = cleanup_service.get_status()
            
            self.assertIsInstance(status, dict, "Should return dict status")
            self.assertIn('enabled', status, "Should have enabled status")
            self.assertIn('retention_days', status, "Should have retention days")
            self.assertIn('video_dir', status, "Should have video directory")
            
            # Check values match our configuration
            self.assertTrue(status['enabled'], "Should be enabled")
            self.assertEqual(status['retention_days'], 7, "Should have 7 day retention")
            self.assertEqual(status['video_dir'], self.test_dir, "Should have correct video directory")
            
    def test_error_handling_integration(self):
        """Test error handling in integrated cleanup workflow"""
        with patch.object(config, 'VIDEO_DIR', self.test_dir), \
             patch.object(config, 'CLEANUP_OLD_VIDEOS', True), \
             patch.object(config, 'VIDEO_RETENTION_DAYS', 7):
            cleanup_service = VideoCleanupService()
            
            # Test with non-existent directory
            nonexistent_dir = "/path/to/nonexistent/directory"
            
            async def cleanup_nonexistent():
                return await cleanup_service.perform_cleanup(nonexistent_dir, dry_run=False)
                
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(cleanup_nonexistent())
            finally:
                loop.close()
                
            # Should handle gracefully
            self.assertIsInstance(results, dict, "Should return results dict")
            self.assertFalse(results['enabled'], "Should handle directory error gracefully")
            
    def test_cleanup_with_different_retention_periods(self):
        """Test cleanup with different retention periods"""
        test_retentions = [3, 7, 14]
        
        for retention in test_retentions:
            with patch.object(config, 'VIDEO_DIR', self.test_dir), \
                 patch.object(config, 'CLEANUP_OLD_VIDEOS', True), \
                 patch.object(config, 'VIDEO_RETENTION_DAYS', retention):
                cleanup_service = VideoCleanupService()
                
                # Get what would be cleaned up
                async def get_cleanup_info():
                    return await cleanup_service.get_cleanup_info(self.test_dir)
                    
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    info = loop.run_until_complete(get_cleanup_info())
                finally:
                    loop.close()
                    
                # Should work with different retention periods
                self.assertIsInstance(info, dict, f"Should return info for {retention} day retention")
                self.assertEqual(info['retention_days'], retention, f"Should have correct retention days")


if __name__ == '__main__':
    unittest.main()
