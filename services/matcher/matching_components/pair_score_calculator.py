"""Pair scoring helpers for individual image/frame combinations."""

from typing import Any, Dict

import numpy as np

from common_py.logging_config import configure_logging

logger = configure_logging("matcher:pair_score_calculator")


class PairScoreCalculator:
    """Calculate similarity scores for image/frame pairs."""

    def __init__(self, sim_deep_min: float, inliers_min: float) -> None:
        self.sim_deep_min = sim_deep_min
        self.inliers_min = inliers_min

    async def calculate_pair_score(
        self,
        image: Dict[str, Any],
        frame: Dict[str, Any],
    ) -> float:
        """Calculate a weighted similarity score for an image-frame pair."""

        try:
            sim_deep = await self.calculate_embedding_similarity(image, frame)
            sim_kp = await self.calculate_keypoint_similarity(image, frame)
            sim_edge = np.random.uniform(0.6, 0.9)

            pair_score = (
                0.35 * sim_deep
                + 0.55 * sim_kp
                + 0.10 * sim_edge
            )

            logger.debug(
                "Calculated pair score",
                img_id=image["img_id"],
                frame_id=frame["frame_id"],
                sim_deep=sim_deep,
                sim_kp=sim_kp,
                sim_edge=sim_edge,
                pair_score=pair_score,
            )

            return pair_score
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to calculate pair score", error=str(exc))
            return 0.0

    async def calculate_embedding_similarity(
        self,
        image: Dict[str, Any],
        frame: Dict[str, Any],
    ) -> float:
        """Calculate embedding similarity between an image and a frame."""

        try:
            if not image.get("emb_rgb") or not frame.get("emb_rgb"):
                return np.random.uniform(0.7, 0.9)

            image_emb = np.array(image["emb_rgb"], dtype=np.float32)
            frame_emb = np.array(frame["emb_rgb"], dtype=np.float32)

            similarity = np.dot(image_emb, frame_emb) / (
                np.linalg.norm(image_emb) * np.linalg.norm(frame_emb)
            )

            return max(0.0, min(1.0, similarity))
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to calculate embedding similarity",
                error=str(exc),
            )
            return 0.0

    async def calculate_keypoint_similarity(
        self,
        image: Dict[str, Any],
        frame: Dict[str, Any],
    ) -> float:
        """Calculate keypoint similarity using a mock RANSAC flow."""

        try:
            if not image.get("kp_blob_path") or not frame.get("kp_blob_path"):
                return np.random.uniform(0.3, 0.7)

            inliers_ratio = np.random.uniform(0.2, 0.8)

            if inliers_ratio < self.inliers_min:
                return 0.0

            return inliers_ratio
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to calculate keypoint similarity",
                error=str(exc),
            )
            return 0.0
