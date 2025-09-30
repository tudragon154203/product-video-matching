#!/usr/bin/env python3
"""
Manual validation script for TikTok video download functionality.
Tests the URL: https://www.tiktok.com/@lanxinx/video/7548644205690670337
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from platform_crawler.tiktok.tiktok_downloader import TikTokDownloader
from common_py.logging_config import configure_logging
from config_loader import config

# Configure logging
logger = configure_logging("tiktok-manual-test")

import pytest

@pytest.mark.integration
async def test_tiktok_download():
    """Test TikTok video download with the specified URL"""
    
    # Test URL
    test_url = "https://www.tiktok.com/@lanxinx/video/7548644205690670337"
    video_id = "test-tiktok-video-123"
    
    print(f"Testing TikTok video download...")
    print(f"URL: {test_url}")
    print(f"Video ID: {video_id}")
    print(f"Video storage path: {config.TIKTOK_VIDEO_STORAGE_PATH}")
    print(f"Keyframe storage path: {config.TIKTOK_KEYFRAME_STORAGE_PATH}")
    print("-" * 60)
    
    # Create downloader configuration
    downloader_config = {
        'TIKTOK_VIDEO_STORAGE_PATH': config.TIKTOK_VIDEO_STORAGE_PATH,
        'TIKTOK_KEYFRAME_STORAGE_PATH': config.TIKTOK_KEYFRAME_STORAGE_PATH,
        'retries': 3,
        'timeout': 30
    }
    
    # Initialize downloader
    downloader = TikTokDownloader(downloader_config)
    
    try:
        # Test 1: Download video
        print("1. Testing video download...")
        video_path = downloader.download_video(test_url, video_id)
        
        if video_path:
            print(f"✅ Video downloaded successfully: {video_path}")
            print(f"   File size: {os.path.getsize(video_path)} bytes")
            
            # Verify file exists and is readable
            if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                print("✅ Video file validation passed")
            else:
                print("❌ Video file validation failed")
                return False
                
        else:
            print("❌ Video download failed")
            return False
        
        print()
        
        # Test 2: Extract keyframes
        print("2. Testing keyframe extraction...")
        keyframes_dir = await downloader.extract_keyframes(video_path, video_id)
        
        if keyframes_dir:
            print(f"✅ Keyframes extracted to: {keyframes_dir}")
            
            # Check for keyframe files
            keyframe_files = list(Path(keyframes_dir).glob("*.jpg"))
            print(f"   Keyframe files found: {len(keyframe_files)}")
            
            if keyframe_files:
                print("✅ Keyframe files validation passed")
                for i, kf_file in enumerate(keyframe_files[:5]):  # Show first 5
                    print(f"   - {kf_file.name} ({kf_file.stat().st_size} bytes)")
                if len(keyframe_files) > 5:
                    print(f"   ... and {len(keyframe_files) - 5} more")
            else:
                print("⚠️  No keyframe files found (extraction may have succeeded but no frames were extracted)")
                
        else:
            print("❌ Keyframe extraction failed")
            return False
        
        print()
        
        # Test 3: Full orchestration
        print("3. Testing full orchestration (download + extraction + database)...")
        
        # Mock database object for testing
        class MockDB:
            def execute(self, query, *args):
                print(f"   Mock DB execute: {query % args if args else query}")
                return True
        
        mock_db = MockDB()
        
        success = await downloader.orchestrate_download_and_extract(
            url=test_url,
            video_id=video_id,
            db=mock_db
        )
        
        if success:
            print("✅ Full orchestration completed successfully")
        else:
            print("❌ Full orchestration failed")
            return False
        
        print()
        
        # Test 4: Verify file system structure
        print("4. Verifying file system structure...")
        
        # Check video file
        expected_video_path = Path(config.TIKTOK_VIDEO_STORAGE_PATH) / f"{video_id}.mp4"
        if expected_video_path.exists():
            print(f"✅ Video file exists at expected location: {expected_video_path}")
        else:
            print(f"❌ Video file not found at expected location: {expected_video_path}")
        
        # Check keyframes directory
        expected_keyframes_dir = Path(config.TIKTOK_KEYFRAME_STORAGE_PATH) / video_id
        if expected_keyframes_dir.exists():
            print(f"✅ Keyframes directory exists: {expected_keyframes_dir}")
            
            # List keyframe files
            kf_files = list(expected_keyframes_dir.glob("*.jpg"))
            print(f"   Keyframe files: {len(kf_files)}")
        else:
            print(f"❌ Keyframes directory not found: {expected_keyframes_dir}")
        
        print()
        
        # Summary
        print("🎉 TikTok video download test completed successfully!")
        print(f"   Video downloaded: {'✅' if video_path else '❌'}")
        print(f"   Keyframes extracted: {'✅' if keyframes_dir else '❌'}")
        print(f"   Full orchestration: {'✅' if success else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@pytest.mark.integration
async def test_cleanup():
    """Test TikTok video cleanup functionality"""
    print("\n" + "="*60)
    print("Testing TikTok video cleanup...")
    
    from services.cleanup_service import cleanup_service
    
    try:
        # Test cleanup
        result = await cleanup_service.cleanup_tiktok_videos(days=7)
        
        print(f"Cleanup result:")
        print(f"   Videos removed: {len(result['videos_removed'])}")
        print(f"   Videos kept: {len(result['videos_skipped'])}")
        print(f"   Size freed: {result['size_freed_mb']:.2f} MB")
        
        if result['videos_removed']:
            print("   Removed videos:")
            for video in result['videos_removed'][:3]:  # Show first 3
                print(f"     - {video['filename']} ({video['size_bytes']} bytes)")
            if len(result['videos_removed']) > 3:
                print(f"     ... and {len(result['videos_removed']) - 3} more")
        
        return True
        
    except Exception as e:
        print(f"❌ Cleanup test failed: {str(e)}")
        return False

@pytest.mark.integration
async def main():
    """Main test function"""
    print("🚀 Starting TikTok Video Download Manual Validation")
    print("=" * 60)
    
    # Test download functionality
    download_success = await test_tiktok_download()
    
    # Test cleanup functionality
    cleanup_success = await test_cleanup()
    
    # Final summary
    print("\n" + "="*60)
    print("📋 FINAL TEST SUMMARY")
    print("=" * 60)
    print(f"Download test: {'✅ PASSED' if download_success else '❌ FAILED'}")
    print(f"Cleanup test: {'✅ PASSED' if cleanup_success else '❌ FAILED'}")
    
    if download_success and cleanup_success:
        print("\n🎉 ALL TESTS PASSED! TikTok video download feature is ready.")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED. Please check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)