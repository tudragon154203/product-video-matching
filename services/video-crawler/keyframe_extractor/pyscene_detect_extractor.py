"""PySceneDetect-based keyframe extractor implementation."""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

try:  # pragma: no cover - imported lazily in tests
    from scenedetect import SceneManager
    from scenedetect.detectors import AdaptiveDetector
    from scenedetect.detectors.content_detector import ContentDetector
    from scenedetect.stats_manager import StatsManager
    from scenedetect.video_manager import VideoManager
except ImportError:  # pragma: no cover
    SceneManager = None
    AdaptiveDetector = None
    ContentDetector = None
    StatsManager = None
    VideoManager = None

from common_py.logging_config import configure_logging
from config_loader import PySceneDetectSettings, config

from .abstract_extractor import AbstractKeyframeExtractor

logger = configure_logging("video-crawler:pyscene_detect_extractor")


class PySceneDetectKeyframeExtractor(AbstractKeyframeExtractor):
    """Keyframe extractor that relies on PySceneDetect scene boundaries."""

    def __init__(
        self,
        keyframe_root_dir: Optional[str] = None,
        settings: Optional[PySceneDetectSettings] = None,
        create_dirs: bool = True,
    ) -> None:
        super().__init__(keyframe_root_dir, create_dirs=create_dirs)
        base_settings = settings or config.PYSCENEDETECT_SETTINGS
        # Copy to decouple from global mutable state
        self.settings = replace(base_settings)

    async def _extract_frames_from_video(
        self,
        video_path: str,
        keyframe_dir: Path,
        video_id: str,
    ) -> List[Tuple[float, str]]:
        if cv2 is None:
            raise RuntimeError("OpenCV is required for keyframe extraction")
        if SceneManager is None or AdaptiveDetector is None or VideoManager is None:
            raise RuntimeError("PySceneDetect is not available. Install scenedetect[opencv].")

        start_time = time.time()
        cap = self._open_video_capture(video_path, video_id)
        try:
            video_props = self._get_video_properties(cap, video_id)
            scene_boundaries = self._detect_scenes(video_path)
            if not scene_boundaries:
                logger.debug("No scenes detected; using full duration", video_id=video_id)
                scene_boundaries = [(0.0, video_props.duration)]

            timestamps = self._select_midpoint_timestamps(scene_boundaries, video_props.duration)
            if not timestamps:
                logger.warning(
                    "No candidate timestamps generated after scene detection",
                    video_id=video_id,
                    scenes=len(scene_boundaries)
                )
                return []

            extracted_frames: List[Tuple[float, str]] = []
            blur_rejections = 0
            read_failures = 0

            for idx, timestamp in enumerate(timestamps):
                if not self._seek_to_timestamp(cap, timestamp, video_props.fps):
                    read_failures += 1
                    continue

                ret, frame = cap.read()
                if not ret or frame is None:
                    read_failures += 1
                    logger.warning("Failed to read frame at timestamp", video_id=video_id, ts=timestamp)
                    continue

                blur_score = self._calculate_blur_score(frame)
                if blur_score < self.settings.min_blur_threshold:
                    blur_rejections += 1
                    logger.debug(
                        "Frame rejected due to blur",
                        video_id=video_id,
                        ts=timestamp,
                        blur_score=blur_score,
                        threshold=self.settings.min_blur_threshold
                    )
                    continue

                frame_filename = self._generate_frame_filename(
                    video_id,
                    timestamp,
                    format=self.settings.frame_format
                )
                frame_path = keyframe_dir / frame_filename

                if self._save_frame(frame, str(frame_path), self.settings.frame_quality):
                    extracted_frames.append((timestamp, str(frame_path)))
                else:
                    read_failures += 1

            logger.info(
                "PySceneDetect extraction finished",
                video_id=video_id,
                scenes=len(scene_boundaries),
                candidate_timestamps=len(timestamps),
                extracted=len(extracted_frames),
                blur_rejections=blur_rejections,
                read_failures=read_failures,
                elapsed_ms=int((time.time() - start_time) * 1000)
            )
            return extracted_frames

        finally:
            if cap is not None:
                cap.release()

    def _detect_scenes(self, video_path: str) -> List[Tuple[float, float]]:
        """Run PySceneDetect to obtain scene boundaries in seconds."""
        if SceneManager is None or AdaptiveDetector is None or VideoManager is None:
            raise RuntimeError("PySceneDetect is not available")

        video_manager = VideoManager([video_path])
        
        # Fast mode: no StatsManager when frame_skip > 0
        # StatsManager doesn't support frame skipping
        if self.settings.frame_skip > 0:
            scene_manager = SceneManager()
        else:
            stats_manager = StatsManager()
            scene_manager = SceneManager(stats_manager)

        weights = ContentDetector.Components(
            delta_lum=1.0,
            delta_hue=0.0 if self.settings.weights_luma_only else 1.0,
            delta_sat=0.0 if self.settings.weights_luma_only else 1.0,
            delta_edges=0.0
        )
        detector = AdaptiveDetector(
            adaptive_threshold=self.settings.adaptive_threshold,
            min_scene_len=self.settings.min_scene_len,
            window_width=self.settings.window_width,
            min_content_val=self.settings.min_content_val,
            weights=weights
        )
        scene_manager.add_detector(detector)

        boundaries: List[Tuple[float, float]] = []

        try:
            video_manager.start()
            scene_manager.detect_scenes(frame_source=video_manager, frame_skip=self.settings.frame_skip)

            # Try modern API first (no base_timecode parameter)
            try:
                scene_list = scene_manager.get_scene_list()
            except Exception:
                # Fallback to deprecated API
                base_timecode = video_manager.get_base_timecode()
                scene_list = scene_manager.get_scene_list(base_timecode)

            for start_time, end_time in scene_list:
                start_seconds = max(0.0, start_time.get_seconds())
                end_seconds = max(0.0, end_time.get_seconds())
                if end_seconds <= start_seconds:
                    continue
                boundaries.append((start_seconds, end_seconds))
        finally:
            video_manager.release()

        return boundaries

    def _select_midpoint_timestamps(
        self,
        scenes: List[Tuple[float, float]],
        video_duration: float,
    ) -> List[float]:
        """Convert scene boundaries into midpoint timestamps with guards."""
        timestamps: List[float] = []
        guard = max(0.0, self.settings.boundary_guard_seconds)
        min_duration = max(0.0, self.settings.min_scene_duration_seconds)
        fallback = max(0.0, self.settings.fallback_offset_seconds)
        max_scenes = max(0, self.settings.max_scenes)

        if len(scenes) == 0:
            start = 0.0
            end = max(0.0, video_duration)
            if end <= start:
                return []

            # Extract 5 frames for videos > 10s, 3 frames for videos 5-10s, 1 frame for shorter
            if end > 10:
                num_frames = 5
            elif end > 5:
                num_frames = 3
            else:
                num_frames = 1

            if max_scenes > 0 and num_frames > max_scenes:
                num_frames = max_scenes

            logger.debug("No scenes detected, using fallback multi-frame extraction",
                         video_duration=end,
                         num_frames=num_frames)

            for i in range(num_frames):
                if num_frames == 1:
                    position = start + (end - start) / 2.0
                else:
                    position = start + (i + 0.5) * (end - start) / num_frames

                upper_limit = max(start, end - guard)
                position = min(position, upper_limit)
                position = max(start, position)

                timestamps.append(position)

            return timestamps

        if len(scenes) == 1:
            start, end = scenes[0]
            start = max(0.0, start)
            end = max(start, end)
            if video_duration > 0:
                end = min(end, video_duration)
            duration = end - start
            if duration <= 0:
                return []

            if duration > 10:
                num_frames = 5
            elif duration > 5:
                num_frames = 3
            else:
                num_frames = 1

            if max_scenes > 0 and num_frames > max_scenes:
                num_frames = max_scenes

            logger.debug("Single scene detected, using scene-aware multi-frame extraction",
                         scene_duration=duration,
                         num_frames=num_frames)

            for i in range(num_frames):
                if num_frames == 1:
                    midpoint = start + (duration / 2.0)
                    upper_limit = max(start, end - min(guard, duration / 2.0))
                    midpoint = min(midpoint, upper_limit)
                    if duration < min_duration:
                        midpoint = start + min(duration / 2.0, fallback)
                    midpoint = max(start, min(midpoint, end))
                    timestamps.append(midpoint)
                else:
                    position = start + (i + 0.5) * duration / num_frames
                    upper_limit = max(start, end - guard)
                    position = min(position, upper_limit)
                    position = max(start, position)
                    timestamps.append(position)

            return timestamps

        # Multiple scenes detected - use normal midpoint extraction
        for start, end in scenes:
            start = max(0.0, start)
            if video_duration > 0:
                end = min(end, video_duration)

            if end <= start:
                continue

            duration = end - start
            midpoint = start + (duration / 2.0)
            upper_limit = max(start, end - min(guard, duration / 2.0))
            midpoint = min(midpoint, upper_limit)

            if duration < min_duration:
                midpoint = start + min(duration / 2.0, fallback)

            midpoint = max(start, min(midpoint, end))
            timestamps.append(midpoint)

            if max_scenes and len(timestamps) >= max_scenes:
                break

        return timestamps

    def _open_video_capture(self, video_path: str, video_id: str):
        """Open a cv2.VideoCapture with safe software decoding flags."""
        import os

        old_env: dict[str, Optional[str]] = {}
        env_overrides = {
            'FFMPEG_HWACCEL': 'none',
            'AV1_FORCE_SOFTWARE_DECODER': '1',
            'OPENCV_FFMPEG_CAPTURE_OPTIONS': 'avioflags;direct'
        }

        for key, value in env_overrides.items():
            old_env[key] = os.environ.get(key)
            os.environ[key] = value

        cap = None
        try:
            cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                logger.warning(
                    "FFMPEG backend failed for PySceneDetect extractor, falling back to default",
                    video_id=video_id,
                    video_path=video_path
                )
                cap = cv2.VideoCapture(video_path)

            if not cap or not cap.isOpened():
                raise ValueError(f"Could not open video file: {video_path}")

            return cap
        finally:
            for key, previous in old_env.items():
                if previous is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = previous
