"""Evidence generation helpers for the evidence builder service."""

from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from common_py.logging_config import configure_logging
from evidence_image_renderer import EvidenceImageRenderer

logger = configure_logging("evidence-builder:evidence")


class EvidenceGenerator:
    """Generate visual evidence assets for matches."""

    def __init__(self, data_root: str) -> None:
        self.data_root = Path(data_root)
        self.evidence_dir = self.data_root / "evidence"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.image_renderer = EvidenceImageRenderer()
        self._rng = np.random.default_rng()

    def create_evidence(
        self,
        job_id: str,
        image_path: str,
        frame_path: str,
        img_id: str,
        frame_id: str,
        score: float,
        timestamp: float,
        kp_img_path: Optional[str] = None,
        kp_frame_path: Optional[str] = None,
    ) -> Optional[str]:
        """Create an evidence image showing the matching pair."""
        try:
            # Create job-specific directory
            job_evidence_dir = self.evidence_dir / job_id
            job_evidence_dir.mkdir(parents=True, exist_ok=True)

            evidence_filename = f"{img_id}_{frame_id}.jpg"
            evidence_path = job_evidence_dir / evidence_filename

            product_img = cv2.imread(image_path)
            frame_img = cv2.imread(frame_path)

            if product_img is None or frame_img is None:
                logger.error(
                    "Failed to load images",
                    image_path=image_path,
                    frame_path=frame_path,
                )
                return None

            evidence_img = self.image_renderer.create_side_by_side_comparison(
                product_img,
                frame_img,
                score,
                timestamp,
                img_id,
                frame_id,
                job_id,
            )

            if kp_img_path and kp_frame_path:
                evidence_img = self.add_keypoint_overlays(
                    evidence_img,
                    product_img,
                    frame_img,
                    kp_img_path,
                    kp_frame_path,
                )

            cv2.imwrite(str(evidence_path), evidence_img)

            logger.info(
                "Created evidence image",
                evidence_path=str(evidence_path),
                score=score,
                job_id=job_id,
            )
            return str(evidence_path)
        except (cv2.error, OSError, ValueError) as exc:
            logger.error(
                "Failed to create evidence",
                img_id=img_id,
                frame_id=frame_id,
                error=str(exc),
            )
            return None

    def add_keypoint_overlays(
        self,
        evidence_img: np.ndarray,
        product_img: np.ndarray,
        frame_img: np.ndarray,
        kp_img_path: str,
        kp_frame_path: str,
    ) -> np.ndarray:
        """Add mock keypoint match overlays to the evidence image."""
        try:
            height, width = evidence_img.shape[:2]
            left_center_x = width // 4
            center_y = height // 2
            right_center_x = 3 * width // 4

            for _ in range(5):
                left_x = left_center_x + int(self._rng.integers(-50, 50))
                left_y = center_y + int(self._rng.integers(-50, 50))
                right_x = right_center_x + int(self._rng.integers(-50, 50))
                right_y = center_y + int(self._rng.integers(-50, 50))

                cv2.circle(evidence_img, (left_x, left_y), 3, (0, 0, 255), -1)
                cv2.circle(evidence_img, (right_x, right_y), 3, (0, 0, 255), -1)
                cv2.line(
                    evidence_img,
                    (left_x, left_y),
                    (right_x, right_y),
                    (255, 0, 0),
                    1,
                )

            legend_y = height - 30
            cv2.putText(
                evidence_img,
                "Red: Keypoints, Blue: Matches",
                (20, legend_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
            )
            return evidence_img
        except (cv2.error, ValueError) as exc:
            logger.error("Failed to add keypoint overlays", error=str(exc))
            return evidence_img
