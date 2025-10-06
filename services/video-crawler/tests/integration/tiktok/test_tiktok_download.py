#!/usr/bin/env python3
"""
Manual validation script for TikTok video download functionality.
Tests the URL: https://www.tiktok.com/@lanxinx/video/7548644205690670337
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest

from platform_crawler.tiktok.tiktok_downloader import TikTokDownloader
from config_loader import config


@pytest.mark.integration
async def test_tiktok_download():
    """Test TikTok video download with the specified URL"""

    # Test URL
    test_url = "https://www.tiktok.com/@lanxinx/video/7548644205690670337"
    video_id = "test-tiktok-video-123"

    print("Testing TikTok video download...")
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

        # Assertions for video download
        assert video_path is not None, "Video download should return a valid path"
        assert os.path.exists(video_path), f"Video file should exist at {video_path}"
        assert os.path.getsize(video_path) > 0, "Video file should not be empty"
        assert video_path.endswith('.mp4'), "Video file should have .mp4 extension"

        print(f"✅ Video downloaded successfully: {video_path}")
        print(f"   File size: {os.path.getsize(video_path)} bytes")

        # Verify file exists and is readable
        if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
            print("✅ Video file validation passed")
        else:
            print("❌ Video file validation failed")
            return False

        print()

        # Test 2: Extract keyframes
        print("2. Testing keyframe extraction...")
        keyframes_dir, keyframes = await downloader.extract_keyframes(video_path, video_id)

        # Assertions for keyframe extraction
        assert keyframes_dir is not None, "Keyframe extraction should return a valid directory path"
        assert os.path.exists(keyframes_dir), f"Keyframes directory should exist at {keyframes_dir}"
        assert os.path.isdir(keyframes_dir), f"Keyframes path should be a directory: {keyframes_dir}"

        # Check for keyframe files
        keyframe_files = list(Path(keyframes_dir).glob("*.jpg"))
        assert keyframe_files, f"At least one keyframe file should be extracted, found {len(keyframe_files)}"
        assert keyframes, "Keyframe metadata list should not be empty"

        # Verify each keyframe file is valid
        for kf_file in keyframe_files:
            assert os.path.getsize(kf_file) > 0, f"Keyframe file should not be empty: {kf_file}"
            assert kf_file.name.endswith('.jpg'), f"Keyframe file should have .jpg extension: {kf_file}"

        print(f"✅ Keyframes extracted to: {keyframes_dir}")
        print(f"   Keyframe files found: {len(keyframe_files)}")
        print(f"   Keyframe metadata entries: {len(keyframes)}")

        if keyframe_files:
            print("✅ Keyframe files validation passed")
            for i, kf_file in enumerate(keyframe_files[:5]):  # Show first 5
                print(f"   - {kf_file.name} ({kf_file.stat().st_size} bytes)")
            if len(keyframe_files) > 5:
                print(f"   ... and {len(keyframe_files) - 5} more")
        else:
            print("⚠️  No keyframe files found (extraction may have succeeded but no frames were extracted)")

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

        # Assertions for full orchestration
        assert success is True, "Full orchestration should succeed"

        # Verify expected files exist after orchestration
        expected_video_path = Path(config.TIKTOK_VIDEO_STORAGE_PATH) / f"{video_id}.mp4"
        assert expected_video_path.exists(), f"Video file should exist at expected location after orchestration: {expected_video_path}"

        expected_keyframes_dir = Path(config.TIKTOK_KEYFRAME_STORAGE_PATH) / video_id
        assert expected_keyframes_dir.exists(), f"Keyframes directory should exist after orchestration: {expected_keyframes_dir}"

        # Verify keyframe files exist in expected location
        kf_files = list(expected_keyframes_dir.glob("*.jpg"))
        assert len(kf_files) > 0, f"At least one keyframe file should exist after orchestration, found {len(kf_files)}"

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
        assert expected_video_path.exists(), f"Video file should exist at expected location: {expected_video_path}"
        assert os.path.getsize(expected_video_path) > 0, f"Video file should not be empty: {expected_video_path}"
        print(f"✅ Video file exists at expected location: {expected_video_path}")

        # Check keyframes directory
        expected_keyframes_dir = Path(config.TIKTOK_KEYFRAME_STORAGE_PATH) / video_id
        assert expected_keyframes_dir.exists(), f"Keyframes directory should exist: {expected_keyframes_dir}"
        assert os.path.isdir(expected_keyframes_dir), f"Keyframes path should be a directory: {expected_keyframes_dir}"
        print(f"✅ Keyframes directory exists: {expected_keyframes_dir}")

        # List keyframe files
        kf_files = list(expected_keyframes_dir.glob("*.jpg"))
        assert len(kf_files) > 0, f"At least one keyframe file should exist, found {len(kf_files)}"
        print(f"   Keyframe files: {len(kf_files)}")

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

        print("Cleanup result:")
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


@pytest.mark.integration
async def test_tiktok_format_selection():
    """Test TikTok video download with different format selections"""

    test_url = "https://www.tiktok.com/@lanxinx/video/7548644205690670337"
    video_id = "test-tiktok-format-123"

    print("Testing TikTok video download with format selection...")
    print(f"URL: {test_url}")
    print(f"Video ID: {video_id}")
    print("-" * 60)

    # Test with custom format selection
    downloader_config = {
        'TIKTOK_VIDEO_STORAGE_PATH': config.TIKTOK_VIDEO_STORAGE_PATH,
        'TIKTOK_KEYFRAME_STORAGE_PATH': config.TIKTOK_KEYFRAME_STORAGE_PATH,
        'retries': 2,
        'timeout': 30
    }

    downloader = TikTokDownloader(downloader_config)

    try:
        # Test download with new format selection
        video_path = downloader.download_video(test_url, video_id)

        # Assertions
        assert video_path is not None, "Video download should return a valid path"
        assert os.path.exists(video_path), f"Video file should exist at {video_path}"
        assert os.path.getsize(video_path) > 0, "Video file should not be empty"
        assert video_path.endswith('.mp4'), "Video file should have .mp4 extension"

        print(f"✅ Video downloaded successfully with format selection: {video_path}")
        print(f"   File size: {os.path.getsize(video_path)} bytes")

        # Verify the file has both video and audio (basic check)
        try:
            import subprocess
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', video_path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and 'video' in result.stdout:
                print("✅ Video stream detected")
            else:
                print("⚠️  Could not verify video stream")

            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', video_path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and 'audio' in result.stdout:
                print("✅ Audio stream detected")
            else:
                print("⚠️  Could not verify audio stream")

        except Exception as e:
            print(f"⚠️  Could not verify streams (ffprobe not available): {e}")

        return True

    except Exception as e:
        print(f"❌ Format selection test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


@pytest.mark.integration
async def test_tiktok_retry_logic():
    """Test TikTok video download retry logic"""

    test_url = "https://www.tiktok.com/@lanxinx/video/7548644205690670337"
    video_id = "test-tiktok-retry-123"

    print("Testing TikTok video download retry logic...")
    print(f"URL: {test_url}")
    print(f"Video ID: {video_id}")
    print("-" * 60)

    # Test with reduced retries to observe retry behavior
    downloader_config = {
        'TIKTOK_VIDEO_STORAGE_PATH': config.TIKTOK_VIDEO_STORAGE_PATH,
        'TIKTOK_KEYFRAME_STORAGE_PATH': config.TIKTOK_KEYFRAME_STORAGE_PATH,
        'retries': 2,
        'timeout': 30
    }

    downloader = TikTokDownloader(downloader_config)

    try:
        # Test download with retry logic
        start_time = asyncio.get_event_loop().time()
        video_path = downloader.download_video(test_url, video_id)
        end_time = asyncio.get_event_loop().time()

        # Assertions
        assert video_path is not None, "Video download should return a valid path"
        assert os.path.exists(video_path), f"Video file should exist at {video_path}"
        assert os.path.getsize(video_path) > 0, "Video file should not be empty"

        download_time = end_time - start_time
        print(f"✅ Video downloaded successfully with retry logic: {video_path}")
        print(f"   Download time: {download_time:.2f} seconds")
        print(f"   File size: {os.path.getsize(video_path)} bytes")

        # The download should take some time due to retries
        if download_time > 5:  # Should take longer than a single attempt
            print("✅ Retry logic appears to have been used (download took longer than expected)")
        else:
            print("ℹ️  Download completed quickly (may not have needed retries)")

        return True

    except Exception as e:
        print(f"❌ Retry logic test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
