"""Codec-aware router that chooses between PySceneDetect and PyAV extractors."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from common_py.logging_config import configure_logging
from config_loader import PyAVSettings, config

from .interface import KeyframeExtractorInterface
from .pyav_extractor import PyAVKeyframeExtractor
from .pyscene_detect_extractor import PySceneDetectKeyframeExtractor

logger = configure_logging("video-crawler:keyframe_extractor_router")


class CodecDetector:
    """Simple codec detector using PyAV metadata inspection."""

    def detect(self, video_path: str) -> Optional[str]:
        try:
            import av  # type: ignore
        except Exception:
            logger.warning("PyAV not available; skipping codec detection")
            return None

        if not video_path:
            return None

        try:
            with av.open(video_path) as container:
                for stream in container.streams:
                    if getattr(stream, "type", "") != "video":
                        continue
                    codec_name = None
                    try:
                        codec_name = (
                            getattr(getattr(stream, "codec_context", None), "name", None)
                            or getattr(getattr(stream, "codec", None), "name", None)
                        )
                    except Exception:
                        codec_name = None

                    if codec_name:
                        return str(codec_name).lower()
        except FileNotFoundError:
            logger.warning("Codec detection failed; file not found", video_path=video_path)
        except Exception as exc:
            logger.warning("Codec detection failed via PyAV", video_path=video_path, error=str(exc))

        return None


class ExtractorRouter(KeyframeExtractorInterface):
    """Routes keyframe extraction to the appropriate extractor based on codec."""

    def __init__(
        self,
        pyscene_extractor: KeyframeExtractorInterface,
        pyav_extractor: KeyframeExtractorInterface,
        settings: PyAVSettings,
        codec_detector: Optional[CodecDetector] = None,
    ) -> None:
        self.pyscene_extractor = pyscene_extractor
        self.pyav_extractor = pyav_extractor
        self.settings = settings
        self.codec_detector = codec_detector or CodecDetector()

    async def extract_keyframes(
        self,
        video_url: str,
        video_id: str,
        local_path: Optional[str] = None,
    ) -> List[Tuple[float, str]]:
        if not local_path or not Path(local_path).exists():
            logger.warning("Router received missing or invalid local_path", video_id=video_id)
            return []

        codec = None
        if self.settings.enable_pyav_routing:
            codec = self.codec_detector.detect(local_path)

        primary, fallback = self._select_extractors(codec)
        logger.debug(
            "Extractor routing decision",
            video_id=video_id,
            codec=codec,
            primary=type(primary).__name__,
            fallback=type(fallback).__name__ if fallback else None,
        )

        primary_result = await self._try_extract(primary, video_url, video_id, local_path)
        if primary_result:
            return primary_result

        if fallback:
            fallback_result = await self._try_extract(fallback, video_url, video_id, local_path)
            if fallback_result:
                return fallback_result

        return primary_result or []

    def _select_extractors(self, codec: Optional[str]):
        normalized = (codec or "").lower()
        is_av1 = normalized.startswith("av1") or "av1" in normalized

        if not self.settings.enable_pyav_routing:
            return self.pyscene_extractor, None

        if is_av1:
            fallback = self.pyscene_extractor if self.settings.fallback_to_pyscene else None
            return self.pyav_extractor, fallback

        # Unknown codec: try PySceneDetect first, then PyAV as fallback
        if not normalized:
            return self.pyscene_extractor, self.pyav_extractor

        # Known non-AV1 codecs: stay on PySceneDetect
        return self.pyscene_extractor, None

    async def _try_extract(
        self,
        extractor: KeyframeExtractorInterface,
        video_url: str,
        video_id: str,
        local_path: str,
    ) -> List[Tuple[float, str]]:
        try:
            return await extractor.extract_keyframes(video_url, video_id, local_path)
        except Exception as exc:
            logger.error(
                "Extractor failed",
                extractor=type(extractor).__name__,
                video_id=video_id,
                error=str(exc),
            )
            return []


def build_keyframe_extractor(
    keyframe_dir: Optional[str] = None,
    create_dirs: bool = False,
    pyav_settings: Optional[PyAVSettings] = None,
) -> KeyframeExtractorInterface:
    """
    Construct a codec-aware keyframe extractor router with default extractors.
    """
    pyscene_extractor = PySceneDetectKeyframeExtractor(
        keyframe_root_dir=keyframe_dir,
        create_dirs=create_dirs,
    )
    pyav_extractor = PyAVKeyframeExtractor(
        keyframe_root_dir=keyframe_dir,
        settings=pyav_settings or config.PYAV_SETTINGS,
        create_dirs=create_dirs,
    )

    return ExtractorRouter(
        pyscene_extractor=pyscene_extractor,
        pyav_extractor=pyav_extractor,
        settings=pyav_settings or config.PYAV_SETTINGS,
    )
