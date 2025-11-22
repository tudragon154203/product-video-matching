"""Performance tests for PySceneDetect keyframe extractor with real videos."""

import shutil
import tempfile
import time
from pathlib import Path
from typing import List

import pytest

from config_loader import PySceneDetectSettings
from keyframe_extractor.pyscene_detect_extractor import PySceneDetectKeyframeExtractor


pytestmark = pytest.mark.integration


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    temp_path = tempfile.mkdtemp(prefix="test_pyscene_perf_")
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def extractor(temp_dir):
    """Create extractor with lenient settings for test videos."""
    settings = PySceneDetectSettings(
        adaptive_threshold=1.0,
        min_scene_len=3,
        window_width=2,
        min_content_val=5.0,
        weights_luma_only=True,
        min_scene_duration_seconds=0.2,
        boundary_guard_seconds=0.05,
        fallback_offset_seconds=0.1,
        min_blur_threshold=30.0,
        frame_quality=90,
        frame_format="jpg",
        max_scenes=20
    )
    return PySceneDetectKeyframeExtractor(keyframe_root_dir=temp_dir, settings=settings)


def find_real_videos(max_videos: int = 5, platforms: List[str] = None) -> List[Path]:
    """Find real videos from the test data directory."""
    video_dir = Path("tests/data/videos")
    
    if not video_dir.exists():
        pytest.skip("No test videos found in tests/data/videos directory")
    
    all_videos = list(video_dir.glob("*.mp4"))
    
    # Filter out videos with problematic filenames (special chars that cause path issues)
    videos = [v for v in all_videos if not any(c in v.stem for c in ['(', ')', '!'])]
    
    if not videos:
        pytest.skip("No suitable .mp4 videos found in tests/data/videos directory")
    
    return videos[:max_videos]


@pytest.mark.asyncio
async def test_pyscene_detect_performance_with_real_videos(extractor, temp_dir):
    """Performance test for PySceneDetect with real videos."""
    videos = find_real_videos(max_videos=2)
    
    results = []
    
    for video_path in videos:
        video_id = video_path.stem
        print(f"\n{'='*70}")
        print(f"Testing video: {video_path.name}")
        print(f"{'='*70}")
        
        # Get video properties
        import cv2
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"⚠️  Could not open video: {video_path}")
            continue
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        cap.release()
        
        print(f"Resolution: {width}x{height}")
        print(f"Duration: {duration:.2f}s")
        print(f"FPS: {fps:.2f}")
        print(f"File size: {file_size_mb:.2f} MB")
        
        # Extract keyframes with timing
        start_time = time.time()
        
        frames = await extractor.extract_keyframes(
            video_url=str(video_path),
            video_id=video_id,
            local_path=str(video_path)
        )
        
        elapsed = time.time() - start_time
        
        # Verify results
        assert len(frames) > 0, f"No frames extracted from {video_path.name}"
        
        # Calculate metrics
        processing_speed = duration / elapsed if elapsed > 0 else 0
        frames_per_second = len(frames) / elapsed if elapsed > 0 else 0
        
        result = {
            "video": video_path.name[:40],
            "resolution": f"{width}x{height}",
            "duration_sec": duration,
            "file_size_mb": file_size_mb,
            "frames_extracted": len(frames),
            "processing_time_sec": elapsed,
            "processing_speed_x": processing_speed,
            "extraction_fps": frames_per_second
        }
        results.append(result)
        
        print(f"\n📊 Results:")
        print(f"  Frames extracted: {len(frames)}")
        print(f"  Processing time: {elapsed:.2f}s")
        print(f"  Processing speed: {processing_speed:.2f}x realtime")
        print(f"  Extraction rate: {frames_per_second:.2f} frames/sec")
        
        # Verify extracted frames exist and are valid
        for timestamp, frame_path in frames:
            assert Path(frame_path).exists(), f"Frame not found: {frame_path}"
            frame_size = Path(frame_path).stat().st_size
            assert frame_size > 0, f"Empty frame: {frame_path}"
            assert frame_size > 1000, f"Frame too small (likely corrupt): {frame_path}"
    
    # Summary
    print(f"\n{'='*70}")
    print("PERFORMANCE SUMMARY")
    print(f"{'='*70}")
    print(f"{'Video':<42} {'Res':<12} {'Dur(s)':<8} {'Frames':<8} {'Time(s)':<10} {'Speed':<8}")
    print(f"{'-'*70}")
    
    for r in results:
        print(f"{r['video']:<42} {r['resolution']:<12} {r['duration_sec']:<8.1f} "
              f"{r['frames_extracted']:<8} {r['processing_time_sec']:<10.2f} {r['processing_speed_x']:<8.2f}x")
    
    avg_speed = sum(r['processing_speed_x'] for r in results) / len(results) if results else 0
    avg_frames = sum(r['frames_extracted'] for r in results) / len(results) if results else 0
    total_duration = sum(r['duration_sec'] for r in results)
    total_time = sum(r['processing_time_sec'] for r in results)
    
    print(f"\n{'='*70}")
    print(f"Average processing speed: {avg_speed:.2f}x realtime")
    print(f"Average frames per video: {avg_frames:.1f}")
    print(f"Total video duration: {total_duration:.1f}s")
    print(f"Total processing time: {total_time:.1f}s")
    print(f"Overall throughput: {total_duration / total_time:.2f}x realtime")
    
    # Performance assertions
    assert len(results) > 0, "No videos were processed"
    assert all(r['frames_extracted'] > 0 for r in results), "Some videos produced no frames"
    assert avg_speed > 0.5, f"Processing too slow: {avg_speed:.2f}x realtime"


@pytest.mark.asyncio
async def test_pyscene_detect_quality_comparison(temp_dir):
    """Compare performance across different quality settings."""
    videos = find_real_videos(max_videos=1)
    video_path = videos[0]
    video_id = video_path.stem
    
    configs = [
        ("Fast", PySceneDetectSettings(
            adaptive_threshold=5.0, min_scene_len=30, window_width=1,
            min_content_val=20.0, weights_luma_only=True,
            min_blur_threshold=50.0, max_scenes=10,
            frame_quality=85, frame_format="jpg"
        )),
        ("Default", PySceneDetectSettings(
            adaptive_threshold=3.0, min_scene_len=15, window_width=2,
            min_content_val=15.0, weights_luma_only=True,
            min_blur_threshold=100.0, max_scenes=50,
            frame_quality=90, frame_format="jpg"
        ))
    ]
    
    results = []
    for config_name, settings in configs:
        extractor = PySceneDetectKeyframeExtractor(
            keyframe_root_dir=temp_dir, settings=settings
        )
        start_time = time.time()
        frames = await extractor.extract_keyframes(
            video_url=str(video_path),
            video_id=video_id,
            local_path=str(video_path)
        )
        elapsed = time.time() - start_time
        results.append({"config": config_name, "frames": len(frames), "time": elapsed})
        assert len(frames) > 0, f"No frames extracted with {config_name} settings"
    
    fast_time = next(r['time'] for r in results if r['config'] == 'Fast')
    default_time = next(r['time'] for r in results if r['config'] == 'Default')
    fast_frames = next(r['frames'] for r in results if r['config'] == 'Fast')
    default_frames = next(r['frames'] for r in results if r['config'] == 'Default')
    
    print(f"\nFast: {fast_frames} frames in {fast_time:.2f}s")
    print(f"Default: {default_frames} frames in {default_time:.2f}s")
    
    # Both configs should extract frames successfully
    assert fast_frames > 0 and default_frames > 0, "Both configs should extract frames"


@pytest.mark.asyncio
async def test_pyscene_detect_batch_processing(extractor):
    """Batch performance test processing multiple videos sequentially."""
    videos = find_real_videos(max_videos=2)
    
    total_frames = 0
    for idx, video_path in enumerate(videos, 1):
        video_id = f"batch_{idx}_{video_path.stem}"
        frames = await extractor.extract_keyframes(
            video_url=str(video_path),
            video_id=video_id,
            local_path=str(video_path)
        )
        total_frames += len(frames)
        assert len(frames) > 0, f"No frames from video {idx}"
    
    assert total_frames > 0, "No frames extracted in batch"





@pytest.mark.asyncio
async def test_pyscene_detect_frame_quality_validation(extractor):
    """Validate quality of extracted frames."""
    videos = find_real_videos(max_videos=1)
    video_path = videos[0]
    video_id = video_path.stem
    
    import cv2
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps > 0 else 0
    cap.release()
    
    frames = await extractor.extract_keyframes(
        video_url=str(video_path),
        video_id=video_id,
        local_path=str(video_path)
    )
    
    assert len(frames) > 0, "No frames extracted"
    
    timestamps = []
    for timestamp, frame_path in frames:
        frame_file = Path(frame_path)
        assert frame_file.exists(), f"Frame file not found: {frame_path}"
        file_size = frame_file.stat().st_size
        assert file_size > 1000, f"Frame too small: {frame_path}"
        assert file_size < 10 * 1024 * 1024, f"Frame too large: {frame_path}"
        timestamps.append(timestamp)
    
    timestamps.sort()
    coverage = (timestamps[-1] - timestamps[0]) / duration * 100 if duration > 0 else 0
    # Coverage should be reasonable - at least a few percent of video
    assert coverage > 1, f"Frames don't cover enough of the video: {coverage:.1f}%"
    assert len(set(timestamps)) == len(timestamps), "Duplicate timestamps found"


@pytest.mark.asyncio
async def test_pyscene_detect_processing_speed_benchmark(extractor):
    """
    Benchmark processing speed to identify performance issues.
    
    This test measures if processing is unreasonably slow, which could indicate:
    - Missing downscaling optimization
    - Inefficient scene detection
    - Hardware acceleration issues
    """
    videos = find_real_videos(max_videos=1)
    video_path = videos[0]
    video_id = video_path.stem
    
    import cv2
    cap = cv2.VideoCapture(str(video_path))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps > 0 else 0
    cap.release()
    
    print(f"\nBenchmark video: {video_path.name}")
    print(f"Resolution: {width}x{height}")
    print(f"Duration: {duration:.2f}s")
    
    start_time = time.time()
    frames = await extractor.extract_keyframes(
        video_url=str(video_path),
        video_id=video_id,
        local_path=str(video_path)
    )
    elapsed = time.time() - start_time
    
    processing_speed = duration / elapsed if elapsed > 0 else 0
    
    print(f"\nProcessing time: {elapsed:.2f}s")
    print(f"Processing speed: {processing_speed:.2f}x realtime")
    print(f"Frames extracted: {len(frames)}")
    
    # Performance expectations
    # For 1080p+ videos, should process at least 0.3x realtime (30s video in 100s)
    # If slower, downscaling should be implemented
    if width * height > 1920 * 1080:
        min_speed = 0.2
        print(f"\nHigh resolution video detected ({width}x{height})")
        print(f"Consider implementing auto_downscale for better performance")
    else:
        min_speed = 0.3
    
    assert len(frames) > 0, "No frames extracted"
    assert processing_speed > min_speed, \
        f"Processing too slow: {processing_speed:.2f}x (expected >{min_speed}x). Consider implementing downscaling."


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])