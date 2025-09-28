"""
Unit tests for VideoCleanupManager
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from utils.file_cleanup import VideoCleanupManager


pytestmark = pytest.mark.unit

class TestVideoCleanupManager(unittest.TestCase):
    """Test cases for VideoCleanupManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.retention_days = 7
        self.cleanup_manager = VideoCleanupManager(self.retention_days)
        
        # Create test video files
        self.create_test_files()
        
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def create_test_files(self):
        """Create test files with different ages"""
        # Current date
        now = datetime.now()
        
        # Create uploader directories
        uploader1 = Path(self.test_dir) / "uploader1"
        uploader2 = Path(self.test_dir) / "uploader2"
        uploader1.mkdir()
        uploader2.mkdir()
        
        # Create recent files (should NOT be cleaned up)
        recent_time = now - timedelta(days=3)
        recent_file1 = uploader1 / "recent_video1.mp4"
        recent_file2 = uploader2 / "recent_video2.avi"
        
        with open(recent_file1, 'w') as f:
            f.write('recent content')
        with open(recent_file2, 'w') as f:
            f.write('recent content')
        
        # Set modification time to be recent
        os.utime(recent_file1, (recent_time.timestamp(), recent_time.timestamp()))
        os.utime(recent_file2, (recent_time.timestamp(), recent_time.timestamp()))
        
        # Create old files (SHOULD be cleaned up)
        old_time = now - timedelta(days=10)
        old_file1 = uploader1 / "old_video1.mp4"
        old_file2 = uploader2 / "old_video2.mkv"
        
        with open(old_file1, 'w') as f:
            f.write('old content')
        with open(old_file2, 'w') as f:
            f.write('old content')
        
        # Set modification time to be old
        os.utime(old_file1, (old_time.timestamp(), old_time.timestamp()))
        os.utime(old_file2, (old_time.timestamp(), old_time.timestamp()))
        
        # Create an empty directory (should be removed after file cleanup)
        empty_dir = uploader1 / "empty"
        empty_dir.mkdir()
        
        # Store references for assertions
        self.recent_files = [str(recent_file1), str(recent_file2)]
        self.old_files = [str(old_file1), str(old_file2)]
        self.empty_dir = str(empty_dir)
        
    def test_should_cleanup_file_with_old_file(self):
        """Test that old files should be cleaned up"""
        old_file = self.old_files[0]
        result = self.cleanup_manager.should_cleanup_file(old_file)
        self.assertTrue(result, "Old files should be marked for cleanup")
        
    def test_should_cleanup_file_with_recent_file(self):
        """Test that recent files should NOT be cleaned up"""
        recent_file = self.recent_files[0]
        result = self.cleanup_manager.should_cleanup_file(recent_file)
        self.assertFalse(result, "Recent files should NOT be marked for cleanup")
        
    def test_should_cleanup_file_with_nonexistent_file(self):
        """Test behavior with non-existent file"""
        nonexistent_file = "/path/to/nonexistent/file.mp4"
        result = self.cleanup_manager.should_cleanup_file(nonexistent_file)
        self.assertFalse(result, "Non-existent files should not be cleaned up")
        
    def test_find_old_files(self):
        """Test finding old video files"""
        old_files = self.cleanup_manager.find_old_files(self.test_dir)
        
        # Should find exactly the old files
        self.assertEqual(len(old_files), 2, "Should find 2 old files")
        
        # Check that all old files are found
        old_file_paths = [f['path'] for f in old_files]
        for old_file in self.old_files:
            self.assertIn(old_file, old_file_paths, f"Old file {old_file} should be found")
        
        # Check that no recent files are found
        for recent_file in self.recent_files:
            self.assertNotIn(recent_file, old_file_paths, f"Recent file {recent_file} should NOT be found")
            
    def test_get_file_info(self):
        """Test file info extraction"""
        uploader_name = "uploader1"
        file_path = Path(self.test_dir) / "uploader1" / "old_video1.mp4"
        file_info = self.cleanup_manager._get_file_info(file_path, uploader_name)
        
        self.assertIsNotNone(file_info, "File info should be returned")
        self.assertEqual(file_info['filename'], "old_video1.mp4")
        self.assertEqual(file_info['uploader'], "uploader1")
        self.assertTrue(file_info['is_old'], "File should be marked as old")
        self.assertIn('file_age_days', file_info, "File age should be calculated")
        
    def test_get_file_info_with_invalid_file(self):
        """Test file info with invalid file path"""
        invalid_path = Path(self.test_dir) / "nonexistent.mp4"
        file_info = self.cleanup_manager._get_file_info(invalid_path, "uploader1")
        self.assertIsNone(file_info, "Invalid file should return None")
        
    def test_cleanup_old_files_dry_run(self):
        """Test cleanup in dry run mode"""
        results = self.cleanup_manager.cleanup_old_files(self.test_dir, dry_run=True)
        
        # No files should be removed in dry run
        self.assertEqual(len(results['files_removed']), 0, "No files should be removed in dry run")
        self.assertEqual(len(results['files_skipped']), 2, "All old files should be listed in skipped")
        self.assertTrue(results['dry_run'], "Should be marked as dry run")
        
        # Files should still exist
        for old_file in self.old_files:
            self.assertTrue(os.path.exists(old_file), "Files should still exist after dry run")
            
    def test_cleanup_old_files_actual_cleanup(self):
        """Test actual file cleanup"""
        # Ensure test files are writable
        for old_file in self.old_files:
            if os.path.exists(old_file):
                os.chmod(old_file, 0o644)
        
        results = self.cleanup_manager.cleanup_old_files(self.test_dir, dry_run=False)
        self.assertGreater(len(results['files_removed']), 0, "Cleanup should remove files when logging")
        self.assertFalse(results['dry_run'], "Cleanup should run in non-dry mode")
        
        # Files should be removed
        self.assertEqual(len(results['files_removed']), 2, "Should remove 2 files")
        self.assertEqual(len(results['files_skipped']), 0, "No files should be skipped")
        self.assertEqual(results['total_size_freed'], 22, "Should free 22 bytes (11 bytes each)")
        self.assertFalse(results['dry_run'], "Should not be marked as dry run")
        
        # Files should no longer exist
        for old_file in self.old_files:
            self.assertFalse(os.path.exists(old_file), f"Old file {old_file} should be removed")
            
        # Recent files should still exist
        for recent_file in self.recent_files:
            self.assertTrue(os.path.exists(recent_file), f"Recent file {recent_file} should still exist")
            
    def test_cleanup_empty_directories(self):
        """Test cleanup of empty directories"""
        # Remove old files first to create empty directories
        for old_file in self.old_files:
            os.remove(old_file)
        
        # Remove recent files too to make uploader dir empty
        for recent_file in self.recent_files:
            if os.path.exists(recent_file):
                os.remove(recent_file)
        
        # Now both uploader1 and uploader2 should be empty (since they only had old files)
        # The "empty" dir is actually uploader1/empty, so uploader1 should be removed completely
        removed_dirs = self.cleanup_manager.cleanup_empty_directories(self.test_dir, dry_run=False)
        
        # Should have removed directories that are now empty
        self.assertTrue(len(removed_dirs) > 0, "Should have removed some directories")
        
        # Check that at least one uploader directory was removed
        uploader_dirs = [str(Path(self.test_dir) / "uploader1"), str(Path(self.test_dir) / "uploader2")]
        removed_uploader_dirs = [d for d in uploader_dirs if d in removed_dirs]
        self.assertTrue(len(removed_uploader_dirs) > 0, "Should have removed uploader directories")
        
    def test_cleanup_empty_directories_dry_run(self):
        """Test dry run for empty directory cleanup"""
        # Remove all files to create empty directories
        for old_file in self.old_files:
            if os.path.exists(old_file):
                os.remove(old_file)
        for recent_file in self.recent_files:
            if os.path.exists(recent_file):
                os.remove(recent_file)
                
        removed_dirs = self.cleanup_manager.cleanup_empty_directories(self.test_dir, dry_run=True)
        
        # Should have listed directories that would be removed
        self.assertTrue(len(removed_dirs) > 0, "Should list directories to be removed")
        self.assertTrue(any('uploader' in d for d in removed_dirs), "Should list uploader directories")
        
    def test_retention_period_setting(self):
        """Test custom retention period"""
        custom_retention = 30
        custom_manager = VideoCleanupManager(custom_retention)
        
        # With 30-day retention, files should NOT be cleaned up
        old_file = self.old_files[0]
        result = custom_manager.should_cleanup_file(old_file)
        self.assertFalse(result, "Files should not be cleaned up with 30-day retention")
        
    @patch('utils.file_cleanup.logger')
    def test_logging_operations(self, mock_logger):
        """Test that appropriate logging occurs"""
        # Ensure test files are writable
        for old_file in self.old_files:
            if os.path.exists(old_file):
                os.chmod(old_file, 0o644)
                
        results = self.cleanup_manager.cleanup_old_files(self.test_dir, dry_run=False)
        self.assertGreater(len(results['files_removed']), 0, "Cleanup should remove files when logging")

        # Verify logging was called
        mock_logger.info.assert_called()
        
        # Should have cleanup summary logged (since files are removed)
        log_calls = [
            log_call.args[0]
            for log_call in mock_logger.info.call_args_list
            if 'CLEANUP-SUMMARY' in log_call.args[0]
        ]
        self.assertTrue(len(log_calls) > 0, "Cleanup summary should be logged when files are removed")
        
    def test_error_handling_for_nonexistent_directory(self):
        """Test error handling for non-existent directory"""
        nonexistent_dir = "/path/to/nonexistent/directory"
        old_files = self.cleanup_manager.find_old_files(nonexistent_dir)
        self.assertEqual(len(old_files), 0, "Should return empty list for non-existent directory")
        
    def test_error_handling_file_permission_error(self):
        """Test error handling when file cannot be removed"""
        # Create a file in an uploader directory that we can't remove by making it read-only
        readonly_file = Path(self.test_dir) / "uploader1" / "readonly.mp4"
        readonly_file.parent.mkdir(parents=True, exist_ok=True)
        with open(readonly_file, 'w') as f:
            f.write('readonly content')
        
        # Set old modification time so it gets cleaned up
        from datetime import datetime, timedelta
        old_time = datetime.now() - timedelta(days=10)
        os.utime(readonly_file, (old_time.timestamp(), old_time.timestamp()))
        
        # Remove the existing files and add our read-only file only
        for old_file in self.old_files:
            if os.path.exists(old_file):
                os.remove(old_file)
        
        # Make it read-only and remove write permissions from parent directory
        readonly_file.chmod(0o444)
        readonly_file.parent.chmod(0o555)  # Remove write permissions from directory
        
        # Try to clean it up - should handle gracefully
        results = self.cleanup_manager.cleanup_old_files(self.test_dir, dry_run=False)
        
        # Should not crash and should handle the error
        self.assertIsInstance(results, dict, "Should return results dict")
        self.assertTrue(len(results['files_skipped']) > 0, "Should skip problematic files")
        self.assertEqual(len(results['files_removed']), 0, "Should not remove any files due to permission error")
        
        # Restore permissions so cleanup can work in teardown
        readonly_file.parent.chmod(0o755)

