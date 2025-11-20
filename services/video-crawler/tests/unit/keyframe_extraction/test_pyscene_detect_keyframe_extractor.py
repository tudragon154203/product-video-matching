"""Unit tests for the PySceneDetect-based keyframe extractor."""

import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from config_loader import PySceneDetectSettings
from keyframe_extractor import pyscene_detect_extractor as extractor_module
from keyframe_extractor.pyscene_detect_extractor import PySceneDetectKeyframeExtractor

pytestmark = pytest.mark.unit


@pytest.fixture
def temp_dir():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def sample_video(temp_dir):
    video_path = Path(temp_dir) / "pyscene_sample.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(video_path), fourcc, 30, (320, 240))
    for i in range(90):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        frame[:, :] = (i % 255, (2 * i) % 255, (3 * i) % 255)
        writer.write(frame)
    writer.release()
    return str(video_path)


@pytest.fixture
def extractor(temp_dir):
    settings = PySceneDetectSettings(
        adaptive_threshold=3.0,
        min_scene_len=5,
        window_width=2,
        min_content_val=10.0,
        weights_luma_only=True,
        downscale_factor=1,
        min_scene_duration_seconds=0.2,
        boundary_guard_seconds=0.05,
        fallback_offset_seconds=0.1,
        min_blur_threshold=10.0,
        frame_quality=90,
        frame_format="jpg",
        max_scenes=0
    )
    return PySceneDetectKeyframeExtractor(keyframe_root_dir=temp_dir, settings=settings)


@pytest.mark.asyncio
async def test_midpoint_selection(extractor, sample_video, monkeypatch):
    scenes = [(0.0, 2.0), (2.0, 4.0)]
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_detect_scenes",
        lambda self, _: scenes
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_calculate_blur_score",
        lambda self, frame: 500.0
    )

    frames = await extractor.extract_keyframes("", "video_midpoint", sample_video)

    assert len(frames) == 2
    assert pytest.approx(frames[0][0], rel=0.05) == 1.0
    assert pytest.approx(frames[1][0], rel=0.05) == 2.5


@pytest.mark.asyncio
async def test_short_scene_clamps_timestamp(extractor, sample_video, monkeypatch):
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_detect_scenes",
        lambda self, _: [(0.0, 0.15)]
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_calculate_blur_score",
        lambda self, frame: 500.0
    )

    frames = await extractor.extract_keyframes("", "video_short", sample_video)
    assert len(frames) == 1
    assert frames[0][0] > 0.0
    assert frames[0][0] < 0.15


@pytest.mark.asyncio
async def test_blur_rejection(extractor, sample_video, monkeypatch):
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_detect_scenes",
        lambda self, _: [(0.0, 1.0)]
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_calculate_blur_score",
        lambda self, frame: 0.0
    )

    frames = await extractor.extract_keyframes("", "video_blur", sample_video)
    assert frames == []


@pytest.mark.asyncio
async def test_detection_failure_returns_empty(extractor, sample_video, monkeypatch):
    def _raise(*_, **__):
        raise RuntimeError("boom")

    monkeypatch.setattr(PySceneDetectKeyframeExtractor, "_detect_scenes", _raise)

    frames = await extractor.extract_keyframes("", "video_fail", sample_video)
    assert frames == []


# NEW TESTS FOR MULTI-FRAME FALLBACK

@pytest.mark.asyncio
async def test_single_scene_long_video_generates_five_timestamps(extractor, sample_video, monkeypatch):
    """Test that single-scene videos > 10s generate 5 evenly-spaced timestamps."""
    from keyframe_extractor.abstract_extractor import AbstractKeyframeExtractor

    # Mock video duration of 15 seconds
    # Need to mock on the base class since _get_video_properties is defined there
    monkeypatch.setattr(
        AbstractKeyframeExtractor,
        "_get_video_properties",
        lambda self, cap, video_id: type('VideoProps', (), {'fps': 30, 'total_frames': 450, 'duration': 15.0, 'width': 320, 'height': 240})
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_detect_scenes",
        lambda self, _: [(0.0, 15.0)]  # single scene
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_seek_to_timestamp",
        lambda self, cap, timestamp, fps: True  # Mock seek as always successful
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_calculate_blur_score",
        lambda self, frame: 500.0
    )

    frames = await extractor.extract_keyframes("", "video_long_single_scene", sample_video)

    # Should generate 5 candidate timestamps for 15s video
    # Note: Actual extraction may fail due to test video limitations, but timestamp generation should work
    assert len(frames) == 5
    # Verify timestamps are evenly spaced: 1.5s, 4.5s, 7.5s, 10.5s, 13.5s (with 0.15s guard)
    assert pytest.approx(frames[0][0], rel=0.1) == 1.35
    assert pytest.approx(frames[1][0], rel=0.1) == 4.5
    assert pytest.approx(frames[2][0], rel=0.1) == 7.5
    assert pytest.approx(frames[3][0], rel=0.1) == 10.5
    assert pytest.approx(frames[4][0], rel=0.1) == 13.35


@pytest.mark.asyncio
async def test_single_scene_medium_video_extracts_three_frames(extractor, sample_video, monkeypatch):
    """Test that single-scene videos 5-10s extract 3 evenly-spaced frames."""
    from keyframe_extractor.abstract_extractor import AbstractKeyframeExtractor

    # Mock video duration of 8 seconds
    # Need to mock on the base class since _get_video_properties is defined there
    monkeypatch.setattr(
        AbstractKeyframeExtractor,
        "_get_video_properties",
        lambda self, cap, video_id: type('VideoProps', (), {'fps': 30, 'total_frames': 240, 'duration': 8.0, 'width': 320, 'height': 240})
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_detect_scenes",
        lambda self, _: [(0.0, 8.0)]  # single scene
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_seek_to_timestamp",
        lambda self, cap, timestamp, fps: True  # Mock seek as always successful
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_calculate_blur_score",
        lambda self, frame: 500.0
    )

    frames = await extractor.extract_keyframes("", "video_medium_single_scene", sample_video)

    # Single scene with duration < 10s should extract 3 frames
    assert len(frames) == 3
    # Verify timestamps are spread across the video (not verifying exact values to avoid brittle tests)
    assert frames[0][0] > 1.0  # early
    assert frames[1][0] > frames[0][0]  # middle
    assert frames[1][0] < frames[2][0]  # middle
    assert frames[2][0] < 8.0  # late


@pytest.mark.asyncio
async def test_single_scene_short_video_extracts_one_frame(extractor, sample_video, monkeypatch):
    """Test that single-scene videos < 5s extract 1 frame at midpoint."""
    from keyframe_extractor.abstract_extractor import AbstractKeyframeExtractor

    # Mock video duration of 3 seconds
    # Need to mock on the base class since _get_video_properties is defined there
    monkeypatch.setattr(
        AbstractKeyframeExtractor,
        "_get_video_properties",
        lambda self, cap, video_id: type('VideoProps', (), {'fps': 30, 'total_frames': 90, 'duration': 3.0, 'width': 320, 'height': 240})
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_detect_scenes",
        lambda self, _: [(0.0, 3.0)]  # single scene
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_seek_to_timestamp",
        lambda self, cap, timestamp, fps: True  # Mock seek as always successful
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_calculate_blur_score",
        lambda self, frame: 500.0
    )

    frames = await extractor.extract_keyframes("", "video_short_single_scene", sample_video)

    # Should extract 1 frame for 3s video
    assert len(frames) == 1
    # Verify timestamp is at midpoint (around 1.4s with boundary guard)
    assert pytest.approx(frames[0][0], rel=0.5) == 1.4


@pytest.mark.asyncio
async def test_multiple_scenes_use_midpoint_extraction(extractor, sample_video, monkeypatch):
    """Test that multi-scene videos still use midpoint extraction."""
    from keyframe_extractor.abstract_extractor import AbstractKeyframeExtractor

    # Mock a 6 second video with 3 scenes
    monkeypatch.setattr(
        AbstractKeyframeExtractor,
        "_get_video_properties",
        lambda self, cap, video_id: type('VideoProps', (), {'fps': 30, 'total_frames': 180, 'duration': 6.0, 'width': 320, 'height': 240})
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_detect_scenes",
        lambda self, _: [(0.0, 2.0), (2.0, 4.0), (4.0, 6.0)]  # 3 scenes
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_seek_to_timestamp",
        lambda self, cap, timestamp, fps: True  # Mock seek as always successful
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_calculate_blur_score",
        lambda self, frame: 500.0
    )

    frames = await extractor.extract_keyframes("", "video_multi_scene", sample_video)

    # Should extract 3 frames (one per scene) at midpoints
    assert len(frames) == 3


@pytest.mark.asyncio
async def test_single_scene_respects_max_scenes(extractor, sample_video, monkeypatch):
    """Test that max_scenes setting limits frames in single-scene mode."""
    from keyframe_extractor.abstract_extractor import AbstractKeyframeExtractor

    # Set max_scenes to 2
    extractor.settings.max_scenes = 2

    # Mock 20 second video (would normally extract 5 frames)
    # Need to mock on the base class since _get_video_properties is defined there
    monkeypatch.setattr(
        AbstractKeyframeExtractor,
        "_get_video_properties",
        lambda self, cap, video_id: type('VideoProps', (), {'fps': 30, 'total_frames': 600, 'duration': 20.0, 'width': 320, 'height': 240})
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_detect_scenes",
        lambda self, _: [(0.0, 20.0)]  # single scene
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_seek_to_timestamp",
        lambda self, cap, timestamp, fps: True  # Mock seek as always successful
    )
    monkeypatch.setattr(
        PySceneDetectKeyframeExtractor,
        "_calculate_blur_score",
        lambda self, frame: 500.0
    )

    frames = await extractor.extract_keyframes("", "video_single_scene_max", sample_video)

    # Should respect max_scenes and extract only 2 frames
    assert len(frames) == 2


@pytest.fixture(autouse=True)
def stub_pyscenedetect(monkeypatch):
    # Tests stub out scene detection internals, so only ensure sentinel objects exist
    for name in ("SceneManager", "AdaptiveDetector", "VideoManager", "StatsManager"):
        monkeypatch.setattr(extractor_module, name, object())
