"""PyAV-based keyframe extractor for AV1 and other problematic codecs."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import List, Optional, Tuple

from common_py.logging_config import configure_logging
from config_loader import PyAVSettings, config

from .abstract_extractor import AbstractKeyframeExtractor

logger = configure_logging("video-crawler:pyav_extractor")


class PyAVKeyframeExtractor(AbstractKeyframeExtractor):
    """Keyframe extractor that uses PyAV for codecs unsupported by OpenCV."""

    def __init__(
        self,
        keyframe_root_dir: Optional[str] = None,
        settings: Optional[PyAVSettings] = None,
        create_dirs: bool = True,
    ) -> None:
        super().__init__(keyframe_root_dir, create_dirs=create_dirs)
        base_settings = settings or config.PYAV_SETTINGS
        # Copy to decouple from global mutable state
        self.settings = replace(base_settings)

    async def _extract_frames_from_video(
        self,
        video_path: str,
        keyframe_dir: Path,
        video_id: str,
    ) -> List[Tuple[float, str]]:
        try:
            import av  # type: ignore
        except Exception as exc:  # pragma: no cover - import guard
            raise RuntimeError("PyAV is required for AV1 keyframe extraction") from exc

        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        container = None
        try:
            container = av.open(video_path)
            stream = self._get_video_stream(container, video_id)
            duration = self._get_duration_seconds(container, stream, video_path)
            timestamps = self._calculate_timestamps(duration)

            logger.info(
                "Starting PyAV extraction",
                video_id=video_id,
                duration_seconds=duration,
                timestamps=timestamps,
            )

            extracted: List[Tuple[float, str]] = []
            for ts in timestamps:
                try:
                    frame_image = self._decode_frame_at_timestamp(video_path, stream.index, ts)
                    if frame_image is None:
                        logger.warning(
                            "PyAV decode returned no frame",
                            video_id=video_id,
                            timestamp=ts,
                        )
                        continue

                    blur_score = self._calculate_blur_score(frame_image)
                    if blur_score < self.settings.min_blur_threshold:
                        logger.debug(
                            "Frame rejected due to blur (PyAV)",
                            video_id=video_id,
                            timestamp=ts,
                            blur_score=blur_score,
                            threshold=self.settings.min_blur_threshold,
                        )
                        continue

                    frame_filename = self._generate_frame_filename(
                        video_id,
                        ts,
                        format=self.settings.frame_format,
                    )
                    frame_path = keyframe_dir / frame_filename

                    if self._save_frame(frame_image, str(frame_path), self.settings.frame_quality):
                        extracted.append((ts, str(frame_path)))
                    else:
                        logger.error(
                            "Failed to save PyAV frame",
                            video_id=video_id,
                            timestamp=ts,
                            frame_path=str(frame_path),
                        )
                except Exception as exc:
                    logger.error(
                        "Error extracting frame via PyAV",
                        video_id=video_id,
                        timestamp=ts,
                        error=str(exc),
                    )
                    continue

            logger.info(
                "PyAV extraction finished",
                video_id=video_id,
                extracted=len(extracted),
                requested=len(timestamps),
            )
            return extracted
        finally:
            if container:
                try:
                    container.close()
                except Exception:
                    logger.debug("Failed to close PyAV container cleanly", video_id=video_id, exc_info=True)

    def _get_video_stream(self, container, video_id: str):
        stream = next((s for s in container.streams if getattr(s, "type", "") == "video"), None)
        if stream is None:
            raise ValueError(f"No video stream found for {video_id}")
        return stream

    def _get_duration_seconds(self, container, stream, source_path: str) -> float:
        try:
            import av  # type: ignore
        except Exception:
            return 0.0

        candidates = []

        if getattr(container, "duration", None):
            try:
                candidates.append(float(container.duration * av.time_base))
            except Exception:
                pass

        if getattr(stream, "duration", None) and getattr(stream, "time_base", None):
            try:
                candidates.append(float(stream.duration * stream.time_base))
            except Exception:
                pass

        if getattr(stream, "average_rate", None) and getattr(stream, "frames", None):
            try:
                if stream.frames and stream.average_rate:
                    candidates.append(float(stream.frames / float(stream.average_rate)))
            except Exception:
                pass

        for candidate in candidates:
            if candidate and 0.0 < candidate < 6 * 3600:  # guard against corrupted durations
                return candidate

        try:
            return float(self.get_video_duration(str(getattr(container, "name", source_path))))
        except Exception:
            logger.warning(
                "Unable to determine video duration via PyAV, defaulting to 0",
                video=str(getattr(container, "name", source_path)),
            )
            return 0.0

    def _calculate_timestamps(self, duration: float) -> List[float]:
        if duration <= 0:
            return [0.0]

        # Simple duration scaling: <=5s →1 frame, <=15s →3 frames, otherwise up to 5
        if duration <= 5:
            target_frames = 1
        elif duration <= 15:
            target_frames = 3
        else:
            target_frames = 5

        target_frames = max(1, min(target_frames, max(1, self.settings.max_frames)))
        guard = max(0.0, self.settings.boundary_guard_seconds)

        timestamps: List[float] = []
        for idx in range(target_frames):
            position = ((idx + 0.5) / target_frames) * duration
            position = min(position, max(0.0, duration - guard))
            timestamps.append(position)

        return timestamps

    def _decode_frame_at_timestamp(self, video_path: str, stream_index: int, timestamp: float):
        """Seek to a timestamp using PyAV and return the closest decoded frame as ndarray."""
        try:
            import av  # type: ignore
        except Exception as exc:  # pragma: no cover - import guard
            raise RuntimeError("PyAV is required for AV1 keyframe extraction") from exc

        with av.open(video_path) as container:
            stream = None
            try:
                stream = container.streams.video[stream_index]
            except Exception:
                stream = next((s for s in container.streams if getattr(s, "type", "") == "video"), None)

            if stream is None:
                return None

            try:
                if getattr(stream, "time_base", None):
                    target_pts = int(timestamp / stream.time_base)
                    container.seek(target_pts, stream=stream, any_frame=False)
            except Exception as exc:
                logger.debug(
                    "PyAV seek failed, falling back to sequential decode",
                    video_path=video_path,
                    timestamp=timestamp,
                    error=str(exc),
                )

            tolerance = max(0.0, self.settings.seek_tolerance_seconds)
            frames_checked = 0

            for frame in container.decode(stream):
                frames_checked += 1
                try:
                    frame_ts = float(frame.pts * frame.time_base) if frame.pts is not None and frame.time_base else None
                except Exception:
                    frame_ts = None

                if frame_ts is not None and frame_ts + tolerance < timestamp:
                    # Seek overshot backwards; continue decoding forward
                    continue

                try:
                    return frame.to_ndarray(format="bgr24")
                except Exception as exc:
                    logger.debug(
                        "Failed to convert PyAV frame to ndarray",
                        video_path=video_path,
                        timestamp=timestamp,
                        error=str(exc),
                    )
                    if frames_checked >= 3:
                        break

            return None
