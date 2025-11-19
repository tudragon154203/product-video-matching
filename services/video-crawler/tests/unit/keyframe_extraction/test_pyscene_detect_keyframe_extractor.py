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
@pytest.fixture(autouse=True)
def stub_pyscenedetect(monkeypatch):
    # Tests stub out scene detection internals, so only ensure sentinel objects exist
    for name in ("SceneManager", "AdaptiveDetector", "VideoManager", "StatsManager"):
        monkeypatch.setattr(extractor_module, name, object())
