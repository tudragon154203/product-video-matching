"""
Length-adaptive keyframe extractor implementation.

This module provides a concrete implementation of keyframe extraction that adapts
the number and timing of extracted frames based on video duration.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

from common_py.logging_config import configure_logging
from .abstract_extractor import AbstractKeyframeExtractor

logger = configure_logging("video-crawler:length_adaptive_extractor")


@dataclass
class KeyframeConfig:
    """Configuration for keyframe extraction"""
    SHORT_VIDEO_RATIO = [0.2, 0.5, 0.8]
    MEDIUM_VIDEO_TIMESTAMPS = [10.0, 30.0, 50.0]
    LONG_VIDEO_TIMESTAMPS = [10.0, 30.0, 60.0, 90.0]
    VERY_LONG_VIDEO_TIMESTAMPS = [10.0, 30.0, 60.0, 90.0, 120.0]

    MIN_BLUR_THRESHOLD = 100.0
    FRAME_BUFFER_SECONDS = 1.0

    FRAME_QUALITY = 95
    FRAME_FORMAT = "jpg"


class LengthAdaptiveKeyframeExtractor(AbstractKeyframeExtractor):
    """Keyframe extractor that adapts extraction strategy based on video length."""

    def __init__(
        self,
        keyframe_root_dir: Optional[str] = None,
        config_override: Optional[KeyframeConfig] = None,
        create_dirs: bool = True,
    ):
        super().__init__(keyframe_root_dir, create_dirs)
        self.config = config_override or KeyframeConfig()

    async def _extract_frames_from_video(
        self,
        video_path: str,
        keyframe_dir: Path,
        video_id: str,
    ) -> List[Tuple[float, str]]:
        if cv2 is None:
            raise RuntimeError("OpenCV is not available")

        cap = None
        try:
            # Set environment variables to force software AV1 decoding
            import os
            old_env = {}
            av1_env_vars = {
                'FFMPEG_HWACCEL': 'none',
                'AV1_FORCE_SOFTWARE_DECODER': '1',
                'OPENCV_FFMPEG_CAPTURE_OPTIONS': 'avioflags;direct'
            }

            for key, value in av1_env_vars.items():
                old_env[key] = os.environ.get(key)
                os.environ[key] = value

            try:
                # Try to open video with FFMPEG backend
                cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)

                if not cap.isOpened():
                    # Fallback: try opening without specific backend
                    logger.warning(
                        "FFMPEG backend failed, trying default backend",
                        video_id=video_id,
                        video_path=video_path
                    )
                    cap = cv2.VideoCapture(video_path)

                if not cap.isOpened():
                    raise ValueError(f"Could not open video file: {video_path}")

            finally:
                # Restore original environment variables
                for key, old_value in old_env.items():
                    if old_value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = old_value

            video_props = self._get_video_properties(cap, video_id)
            if video_props.duration <= 0:
                raise ValueError(f"Invalid video duration: {video_props.duration}")

            timestamps = self._calculate_extraction_timestamps(video_props)

            logger.info(
                "Starting frame extraction",
                video_id=video_id,
                timestamps=timestamps,
                video_duration=video_props.duration,
            )

            keyframes = await self._extract_frames_at_timestamps(
                cap, timestamps, keyframe_dir, video_id, video_props
            )

            return keyframes

        finally:
            if cap is not None:
                cap.release()

    def _calculate_extraction_timestamps(self, video_props) -> List[float]:
        duration = video_props.duration

        if duration <= 2.0:
            return [duration / 2.0]

        if duration <= 30.0:
            timestamps = [duration * ratio for ratio in self.config.SHORT_VIDEO_RATIO]
        elif duration <= 60.0:
            timestamps = self.config.MEDIUM_VIDEO_TIMESTAMPS[:]
        elif duration <= 120.0:
            timestamps = self.config.LONG_VIDEO_TIMESTAMPS[:]
        else:
            timestamps = self.config.VERY_LONG_VIDEO_TIMESTAMPS[:]

        buffer = self.config.FRAME_BUFFER_SECONDS
        valid_timestamps = [ts for ts in timestamps if ts < (duration - buffer)]

        if not valid_timestamps and timestamps:
            valid_timestamps = [duration / 2.0]

        logger.debug(
            "Calculated extraction timestamps",
            video_duration=duration,
            original_timestamps=timestamps,
            valid_timestamps=valid_timestamps,
            filtered_count=len(timestamps) - len(valid_timestamps),
        )

        return valid_timestamps

    async def _extract_frames_at_timestamps(
        self,
        cap,
        timestamps: List[float],
        keyframe_dir: Path,
        video_id: str,
        video_props,
    ) -> List[Tuple[float, str]]:
        if cv2 is None:
            raise RuntimeError("OpenCV is not available")

        extracted_frames: List[Tuple[float, str]] = []

        for timestamp in timestamps:
            try:
                if not self._seek_to_timestamp(cap, timestamp, video_props.fps):
                    logger.warning(
                        "Failed to seek to timestamp",
                        video_id=video_id,
                        timestamp=timestamp,
                    )
                    continue

                ret, frame = cap.read()
                if not ret or frame is None:
                    logger.warning(
                        "Failed to read frame at timestamp",
                        video_id=video_id,
                        timestamp=timestamp,
                    )
                    continue

                blur_score = self._calculate_blur_score(frame)
                if blur_score < self.config.MIN_BLUR_THRESHOLD:
                    logger.debug(
                        "Frame rejected due to blur",
                        video_id=video_id,
                        timestamp=timestamp,
                        blur_score=blur_score,
                        threshold=self.config.MIN_BLUR_THRESHOLD,
                    )

                frame_filename = self._generate_frame_filename(
                    video_id, timestamp, self.config.FRAME_FORMAT
                )
                frame_path = keyframe_dir / frame_filename

                if self._save_frame(frame, str(frame_path), self.config.FRAME_QUALITY):
                    extracted_frames.append((timestamp, str(frame_path)))
                else:
                    logger.error(
                        "Failed to save frame",
                        video_id=video_id,
                        timestamp=timestamp,
                        frame_path=str(frame_path),
                    )

            except Exception as exc:
                logger.error(
                    "Error extracting frame at timestamp",
                    video_id=video_id,
                    timestamp=timestamp,
                    error=str(exc),
                )
                continue

        logger.info(
            "Frame extraction completed",
            video_id=video_id,
            total_extracted=len(extracted_frames),
            total_requested=len(timestamps),
        )

        return extracted_frames
