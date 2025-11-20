"""
PyAV Demo Script: Test AV1 Video Processing

This script tests whether PyAV can successfully process AV1-encoded videos
that fail with OpenCV/FFmpeg. It tests:
1. Opening AV1 videos with PyAV
2. Seeking to specific timestamps
3. Decoding frames
4. Comparing with OpenCV behavior

Usage:
    python tests/pyav_av1_demo.py <video_path>

Example:
    python tests/pyav_av1_demo.py "My 500k chair #shorts.mp4"
"""

import sys
import cv2
import av
from pathlib import Path
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_opencv(video_path):
    """Test video processing with OpenCV - should fail for AV1 videos."""
    logger.info("=" * 80)
    logger.info("Testing OpenCV (expected to fail on AV1 videos)")
    logger.info("=" * 80)

    results = {
        "can_open": False,
        "can_seek_frame": False,
        "can_seek_timestamp": False,
        "can_read_frame": False,
        "error_messages": []
    }

    try:
        # Test 1: Open video
        logger.info("\n[OpenCV] Test 1: Opening video file...")
        cap = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG)

        if not cap.isOpened():
            results["error_messages"].append("Failed to open video")
            logger.error("[OpenCV] Failed to open video!")
            return results

        results["can_open"] = True
        logger.info(f"[OpenCV] ✓ Video opened successfully")

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0

        logger.info(f"[OpenCV] FPS: {fps:.2f}")
        logger.info(f"[OpenCV] Frame count: {frame_count}")
        logger.info(f"[OpenCV] Duration: {duration:.2f}s")

        # Test 2: Frame-based seek (CAP_PROP_POS_FRAMES)
        logger.info("\n[OpenCV] Test 2: Frame-based seek...")
        target_frame = min(90, frame_count // 2)  # Frame at ~3 seconds
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        actual_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)

        frame_seek_worked = abs(actual_frame - target_frame) <= 5
        results["can_seek_frame"] = frame_seek_worked

        if frame_seek_worked:
            logger.info(f"[OpenCV] ✓ Frame-based seek worked: {actual_frame:.0f} ≈ {target_frame}")
        else:
            logger.error(f"[OpenCV] ✗ Frame-based seek failed: {actual_frame:.0f} != {target_frame}")
            results["error_messages"].append(f"Frame seek failed: got {actual_frame}, expected {target_frame}")

        # Test 3: Timestamp-based seek (CAP_PROP_POS_MSEC)
        logger.info("\n[OpenCV] Test 3: Timestamp-based seek...")
        target_timestamp_ms = 3000  # 3 seconds
        cap.set(cv2.CAP_PROP_POS_MSEC, target_timestamp_ms)
        actual_timestamp = cap.get(cv2.CAP_PROP_POS_MSEC)

        timestamp_seek_worked = abs(actual_timestamp - target_timestamp_ms) <= 100
        results["can_seek_timestamp"] = timestamp_seek_worked

        if timestamp_seek_worked:
            logger.info(f"[OpenCV] ✓ Timestamp-based seek worked: {actual_timestamp:.0f}ms ≈ {target_timestamp_ms}ms")
        else:
            logger.error(f"[OpenCV] ✗ Timestamp-based seek failed: {actual_timestamp:.0f}ms != {target_timestamp_ms}ms")
            results["error_messages"].append(f"Timestamp seek failed: got {actual_timestamp}, expected {target_timestamp_ms}")

        # Test 4: Read frame
        logger.info("\n[OpenCV] Test 4: Reading frame...")
        ret, frame = cap.read()

        if ret and frame is not None:
            results["can_read_frame"] = True
            logger.info(f"[OpenCV] ✓ Frame read successfully: shape {frame.shape}")
        else:
            logger.error("[OpenCV] ✗ Failed to read frame!")
            results["error_messages"].append("Frame read failed")

        cap.release()

    except Exception as e:
        logger.error(f"[OpenCV] Exception: {e}")
        results["error_messages"].append(str(e))

    return results


def test_pyav(video_path):
    """Test video processing with PyAV - should work even for AV1 videos."""
    logger.info("=" * 80)
    logger.info("Testing PyAV (expected to work on AV1 videos)")
    logger.info("=" * 80)

    results = {
        "can_open": False,
        "can_seek": False,
        "can_read_frame": False,
        "can_decode_multiple": False,
        "frames_decoded": 0,
        "stream_info": {},
        "error_messages": []
    }

    try:
        # Test 1: Open video container
        logger.info("\n[PyAV] Test 1: Opening video container...")
        container = av.open(str(video_path))
        results["can_open"] = True
        logger.info(f"[PyAV] ✓ Container opened successfully")
        logger.info(f"[PyAV] Format: {container.format.name}")
        logger.info(f"[PyAV] Duration: {container.duration / 1000000:.2f}s")

        # Get video stream info
        video_stream = container.streams.video[0]
        results["stream_info"] = {
            "codec": video_stream.codec_context.name,
            "width": video_stream.codec_context.width,
            "height": video_stream.codec_context.height,
            "fps": float(video_stream.average_rate),
            "duration": float(video_stream.duration * video_stream.time_base),
        }

        logger.info(f"[PyAV] Video codec: {video_stream.codec_context.name}")
        logger.info(f"[PyAV] Resolution: {video_stream.codec_context.width}x{video_stream.codec_context.height}")
        logger.info(f"[PyAV] FPS: {float(video_stream.average_rate):.2f}")

        # Test 2: Seek to timestamp
        logger.info("\n[PyAV] Test 2: Seeking to 3.0 seconds...")
        target_time = 3.0
        container.seek(int(target_time * 1000000), any_frame=False)  # Seek in microseconds
        results["can_seek"] = True
        logger.info(f"[PyAV] ✓ Seek successful to {target_time}s")

        # Test 3: Decode frame
        logger.info("\n[PyAV] Test 3: Decoding frame...")
        frame_count = 0
        for packet in container.demux(video_stream):
            for frame in packet.decode():
                frame_count += 1
                logger.info(f"[PyAV] ✓ Frame decoded: {frame.width}x{frame.height}, pts={frame.pts}")
                results["can_read_frame"] = True
                break
            if frame_count > 0:
                break

        # Test 4: Decode multiple frames
        logger.info("\n[PyAV] Test 4: Decoding multiple frames...")
        results["frames_decoded"] = 0

        # Seek to beginning
        container.seek(0)

        # Decode 10 frames
        target_frames = 10
        for packet in container.demux(video_stream):
            for frame in packet.decode():
                results["frames_decoded"] += 1
                if results["frames_decoded"] >= target_frames:
                    break
            if results["frames_decoded"] >= target_frames:
                break

        if results["frames_decoded"] >= target_frames:
            results["can_decode_multiple"] = True
            logger.info(f"[PyAV] ✓ Successfully decoded {results['frames_decoded']} frames")
        else:
            logger.warning(f"[PyAV] ⚠ Only decoded {results['frames_decoded']} frames (expected {target_frames})")

        container.close()

    except Exception as e:
        logger.error(f"[PyAV] Exception: {e}")
        import traceback
        traceback.print_exc()
        results["error_messages"].append(str(e))

    return results


def print_summary(opencv_results, pyav_results):
    """Print comparison summary."""
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY: OpenCV vs PyAV")
    logger.info("=" * 80)

    logger.info("\n--- OpenCV Results ---")
    logger.info(f"Can open video: {opencv_results['can_open']}")
    logger.info(f"Can seek by frame: {opencv_results['can_seek_frame']}")
    logger.info(f"Can seek by timestamp: {opencv_results['can_seek_timestamp']}")
    logger.info(f"Can read frame: {opencv_results['can_read_frame']}")
    if opencv_results['error_messages']:
        logger.info(f"Errors: {opencv_results['error_messages']}")

    logger.info("\n--- PyAV Results ---")
    logger.info(f"Can open container: {pyav_results['can_open']}")
    logger.info(f"Can seek: {pyav_results['can_seek']}")
    logger.info(f"Can decode frame: {pyav_results['can_read_frame']}")
    logger.info(f"Can decode multiple: {pyav_results['can_decode_multiple']}")
    logger.info(f"Frames decoded: {pyav_results['frames_decoded']}")
    logger.info(f"Stream info: {pyav_results['stream_info']}")
    if pyav_results['error_messages']:
        logger.info(f"Errors: {pyav_results['error_messages']}")

    logger.info("\n--- Comparison ---")

    if not opencv_results['can_read_frame'] and pyav_results['can_read_frame']:
        logger.info("\n✅ CONCLUSION: PyAV can handle this video, OpenCV cannot!")
        logger.info("   This video is likely AV1-encoded. Use PyAV for extraction.")
        return True

    elif opencv_results['can_read_frame'] and pyav_results['can_read_frame']:
        logger.info("\n⚖️ CONCLUSION: Both OpenCV and PyAV work with this video.")
        logger.info("   This video is likely H.264 or VP9 encoded. OpenCV is sufficient.")
        return False

    elif not opencv_results['can_read_frame'] and not pyav_results['can_read_frame']:
        logger.info("\n❌ CONCLUSION: Neither OpenCV nor PyAV can handle this video.")
        logger.info("   The video may be corrupted or use an unsupported format.")
        return False

    else:
        logger.info("\n❓ CONCLUSION: Unexpected results!")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pyav_av1_demo.py <video_path>")
        print("Example: python pyav_av1_demo.py 'My 500k chair #shorts.mp4'")
        sys.exit(1)

    video_path = Path(sys.argv[1])

    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        sys.exit(1)

    # Test OpenCV (expected to fail on AV1)
    opencv_results = test_opencv(video_path)

    # Test PyAV (expected to work on AV1)
    pyav_results = test_pyav(video_path)

    # Print comparison
    is_av1_success = print_summary(opencv_results, pyav_results)

    # Exit with appropriate code
    sys.exit(0 if is_av1_success else 1)
