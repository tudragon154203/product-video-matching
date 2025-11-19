"""Factory helpers for selecting the configured keyframe extractor."""

from __future__ import annotations

from typing import Optional

from common_py.logging_config import configure_logging

from config_loader import config
from .interface import KeyframeExtractorInterface
from .length_adaptive_extractor import LengthAdaptiveKeyframeExtractor
from .pyscene_detect_extractor import PySceneDetectKeyframeExtractor

logger = configure_logging("video-crawler:keyframe_extractor_factory")


class KeyframeExtractorFactory:
    """Factory object used to build configured keyframe extractors."""

    @staticmethod
    def build(
        strategy: Optional[str] = None,
        keyframe_dir: Optional[str] = None,
        create_dirs: bool = False,
    ) -> KeyframeExtractorInterface:
        resolved = (strategy or config.KEYFRAME_EXTRACTOR_STRATEGY or "pyscene_detect").strip().lower()

        if resolved == "pyscene_detect":
            logger.debug("Initializing PySceneDetect keyframe extractor", keyframe_dir=keyframe_dir)
            return PySceneDetectKeyframeExtractor(keyframe_root_dir=keyframe_dir, create_dirs=create_dirs)

        if resolved == "length_based":
            logger.debug("Initializing length-based keyframe extractor", keyframe_dir=keyframe_dir)
            return LengthAdaptiveKeyframeExtractor(keyframe_root_dir=keyframe_dir, create_dirs=create_dirs)

        raise ValueError(f"Unsupported keyframe extractor strategy: {resolved}")
