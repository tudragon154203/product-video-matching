"""Integration tests for the PyAV extractor and codec-aware router."""

import shutil
import tempfile
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
import pytest

pytest.importorskip("av")

from config_loader import PyAVSettings
from keyframe_extractor.interface import KeyframeExtractorInterface
from keyframe_extractor.pyav_extractor import PyAVKeyframeExtractor
from keyframe_extractor.router import CodecDetector, ExtractorRouter

pytestmark = pytest.mark.integration


@pytest.fixture
def temp_dir():
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def sample_video(temp_dir: str) -> str:
    """Create a small MP4 video with distinct edges for blur scoring."""
    video_path = Path(temp_dir) / "test_video.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = 30
    frame_size = (320, 240)
    duration_seconds = 8
    total_frames = fps * duration_seconds

    out = cv2.VideoWriter(str(video_path), fourcc, fps, frame_size)
    for i in range(total_frames):
        frame = np.zeros((frame_size[1], frame_size[0], 3), dtype=np.uint8)
        cv2.rectangle(frame, (20, 20), (300, 220), (50 + i % 200, 100, 200), 3)
        cv2.putText(frame, f"F{i}", (40, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        out.write(frame)
    out.release()

    return str(video_path)


class StubExtractor(KeyframeExtractorInterface):
    def __init__(self, result: List[Tuple[float, str]], should_raise: bool = False):
        self.result = result
        self.should_raise = should_raise
        self.calls = 0

    async def extract_keyframes(self, video_url: str, video_id: str, local_path=None):
        self.calls += 1
        if self.should_raise:
            raise RuntimeError("boom")
        return self.result


class StubDetector(CodecDetector):
    def __init__(self, codec: str | None):
        self._codec = codec

    def detect(self, video_path: str):
        return self._codec


@pytest.mark.asyncio
async def test_pyav_extractor_extracts_frames(sample_video: str, temp_dir: str):
    settings = PyAVSettings(
        frame_quality=80,
        min_blur_threshold=1.0,
        max_frames=4,
        boundary_guard_seconds=0.1,
        seek_tolerance_seconds=0.5,
    )
    extractor = PyAVKeyframeExtractor(keyframe_root_dir=temp_dir, settings=settings)

    frames = await extractor.extract_keyframes("http://example.com", "vid123", sample_video)

    assert frames
    assert len(frames) <= settings.max_frames
    for ts, path in frames:
        assert isinstance(ts, float)
        saved = Path(path)
        assert saved.exists()
        assert saved.suffix == ".jpg"


@pytest.mark.asyncio
async def test_router_prefers_pyav_for_av1_and_falls_back(sample_video: str, temp_dir: str):
    pyav = StubExtractor(result=[])
    pyscene = StubExtractor(result=[(0.5, str(Path(temp_dir) / "frame.jpg"))])
    settings = PyAVSettings(enable_pyav_routing=True, fallback_to_pyscene=True)
    router = ExtractorRouter(
        pyscene_extractor=pyscene,
        pyav_extractor=pyav,
        settings=settings,
        codec_detector=StubDetector(codec="av1"),
    )

    # Create a tiny placeholder so the router passes existence check
    placeholder = Path(temp_dir) / "placeholder.mp4"
    placeholder.write_text("stub")

    frames = await router.extract_keyframes("", "vid789", str(placeholder))

    assert frames == pyscene.result
    assert pyav.calls == 1  # primary attempt
    assert pyscene.calls == 1  # fallback attempt


@pytest.mark.asyncio
async def test_router_unknown_codec_falls_back_to_pyav(temp_dir: str):
    pyav = StubExtractor(result=[(1.0, str(Path(temp_dir) / "pyav_frame.jpg"))])
    pyscene = StubExtractor(result=[])
    settings = PyAVSettings(enable_pyav_routing=True, fallback_to_pyscene=True)
    router = ExtractorRouter(
        pyscene_extractor=pyscene,
        pyav_extractor=pyav,
        settings=settings,
        codec_detector=StubDetector(codec=None),
    )

    placeholder = Path(temp_dir) / "placeholder.mp4"
    placeholder.write_text("stub")

    frames = await router.extract_keyframes("", "vid001", str(placeholder))

    assert frames == pyav.result
    assert pyscene.calls == 1  # primary
    assert pyav.calls == 1  # fallback


@pytest.mark.asyncio
async def test_router_skips_pyav_when_disabled(temp_dir: str):
    pyav = StubExtractor(result=[(0.1, "noop")])
    pyscene = StubExtractor(result=[(0.2, "scene_frame.jpg")])
    settings = PyAVSettings(enable_pyav_routing=False, fallback_to_pyscene=True)
    router = ExtractorRouter(
        pyscene_extractor=pyscene,
        pyav_extractor=pyav,
        settings=settings,
        codec_detector=StubDetector(codec="av1"),
    )

    placeholder = Path(temp_dir) / "placeholder.mp4"
    placeholder.write_text("stub")

    frames = await router.extract_keyframes("", "vid002", str(placeholder))

    assert frames == pyscene.result
    assert pyscene.calls == 1
    assert pyav.calls == 0
