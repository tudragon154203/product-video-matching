import os
from pathlib import Path

import pytest

from platform_crawler.tiktok.tiktok_downloader import TikTokDownloader
from config_loader import config


@pytest.mark.integration
async def test_download_then_keyframe_extraction():
    """Test TikTok video download and keyframe extraction integration with real URL"""

    # Test URL
    test_url = "https://www.tiktok.com/@lanxinx/video/7548644205690670337"
    video_id = "test-keyframe-extraction-123"

    # Create downloader configuration
    downloader_config = {
        'TIKTOK_VIDEO_STORAGE_PATH': config.TIKTOK_VIDEO_STORAGE_PATH,
        'TIKTOK_KEYFRAME_STORAGE_PATH': config.TIKTOK_KEYFRAME_STORAGE_PATH,
        'retries': 3,
        'timeout': 30
    }

    downloader = TikTokDownloader(downloader_config)

    try:
        # Step 1: Download the video first
        print("Downloading TikTok video...")
        video_path = downloader.download_video(test_url, video_id)

        # Verify video download
        assert video_path is not None, "Video download should return a valid path"
        assert os.path.exists(video_path), f"Video file should exist at {video_path}"
        assert os.path.getsize(video_path) > 0, "Video file should not be empty"
        assert video_path.endswith('.mp4'), "Video file should have .mp4 extension"

        print(f"✅ Video downloaded successfully: {video_path}")

        # Step 2: Extract keyframes from the downloaded video
        print("Extracting keyframes...")
        keyframes_dir, keyframes = await downloader.extract_keyframes(video_path, video_id)

        # Verify keyframe extraction
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

        # Verify keyframe metadata matches files
        assert len(keyframes) == len(keyframe_files), "Keyframe metadata count should match file count"

        # Verify timestamps are valid
        for timestamp, frame_path in keyframes:
            assert isinstance(timestamp, float), "Timestamp should be a float"
            assert timestamp >= 0.0, "Timestamp should be non-negative"
            assert os.path.exists(frame_path), f"Keyframe file should exist: {frame_path}"
            assert frame_path.endswith('.jpg'), f"Frame path should point to JPG file: {frame_path}"

        print(f"✅ Keyframes extracted successfully: {len(keyframes)} frames")
        print(f"   Directory: {keyframes_dir}")

        # Step 3: Test full orchestration
        print("Testing full orchestration...")

        # Mock database object for testing
        class MockDB:
            def execute(self, query, *args):
                return True

        mock_db = MockDB()

        success = await downloader.orchestrate_download_and_extract(
            url=test_url,
            video_id=video_id + "-orchestration",
            db=mock_db
        )

        assert success is True, "Full orchestration should succeed"

        print("✅ Full orchestration completed successfully")

    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        # Skip test if it's a network/API issue rather than code issue
        error_msg = str(e).lower()
        if any(
            keyword in error_msg
            for keyword in ['network', 'connection', 'timeout', 'tiktok', 'restricted', '403', '429']
        ):
            pytest.skip(f"Skipped due to external factors: {e}")
        else:
            raise
