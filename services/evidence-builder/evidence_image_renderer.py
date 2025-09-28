"""Utilities for rendering composite evidence images."""

import cv2
import numpy as np

from common_py.logging_config import configure_logging

logger = configure_logging("evidence-builder:evidence_image_renderer")


class EvidenceImageRenderer:
    """Compose annotated comparison images for evidence output."""

    def create_side_by_side_comparison(
        self,
        product_img: np.ndarray,
        frame_img: np.ndarray,
        score: float,
        timestamp: float,
        img_id: str,
        frame_id: str,
    ) -> np.ndarray:
        """Create side-by-side comparison image."""
        try:
            target_height = 400
            product_resized = self._resize_image(product_img, target_height)
            frame_resized = self._resize_image(frame_img, target_height)

            combined = self._setup_canvas_and_place_images(
                product_resized,
                frame_resized,
            )
            combined = self._add_text_and_borders(
                combined,
                product_resized.shape[1],
                frame_resized.shape[1],
                score,
                timestamp,
                img_id,
                frame_id,
            )
            return combined
        except (cv2.error, ValueError, TypeError) as exc:
            logger.error(
                "Failed to create side-by-side comparison",
                error=str(exc),
            )
            return np.hstack([product_img, frame_img])

    def _resize_image(self, img: np.ndarray, target_height: int) -> np.ndarray:
        height, width = img.shape[:2]
        new_width = int(width * target_height / height)
        return cv2.resize(img, (new_width, target_height))

    def _setup_canvas_and_place_images(
        self,
        product_resized: np.ndarray,
        frame_resized: np.ndarray,
    ) -> np.ndarray:
        padding = 20
        header_height = 80
        footer_height = 60

        total_width = (
            product_resized.shape[1]
            + frame_resized.shape[1]
            + padding * 3
        )
        total_height = product_resized.shape[0] + header_height + footer_height

        combined = np.ones((total_height, total_width, 3), dtype=np.uint8) * 255

        y_offset = header_height
        combined[
            y_offset : y_offset + product_resized.shape[0],
            padding : padding + product_resized.shape[1],
        ] = product_resized
        combined[
            y_offset : y_offset + product_resized.shape[0],
            padding * 2 + product_resized.shape[1] : padding * 2
            + product_resized.shape[1]
            + frame_resized.shape[1],
        ] = frame_resized
        return combined

    def _add_text_and_borders(
        self,
        combined: np.ndarray,
        product_width: int,
        frame_width: int,
        score: float,
        timestamp: float,
        img_id: str,
        frame_id: str,
    ) -> np.ndarray:
        padding = 20
        header_height = 80
        target_height = combined.shape[0] - header_height - 60

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        color = (0, 0, 0)
        thickness = 2

        header_text = f"Product-Video Match (Score: {score:.3f})"
        cv2.putText(
            combined,
            header_text,
            (padding, 30),
            font,
            font_scale,
            color,
            thickness,
        )

        cv2.putText(
            combined,
            "Product Image",
            (padding, header_height - 10),
            font,
            0.6,
            color,
            1,
        )
        cv2.putText(
            combined,
            f"Video Frame (t={timestamp:.1f}s)",
            (padding * 2 + product_width, header_height - 10),
            font,
            0.6,
            color,
            1,
        )

        footer_y = header_height + target_height + 30
        cv2.putText(
            combined,
            f"Image ID: {img_id}",
            (padding, footer_y),
            font,
            0.5,
            color,
            1,
        )
        cv2.putText(
            combined,
            f"Frame ID: {frame_id}",
            (padding * 2 + product_width, footer_y),
            font,
            0.5,
            color,
            1,
        )

        cv2.rectangle(
            combined,
            (padding - 2, header_height - 2),
            (padding + product_width + 2, header_height + target_height + 2),
            (0, 255, 0),
            2,
        )
        cv2.rectangle(
            combined,
            (padding * 2 + product_width - 2, header_height - 2),
            (
                padding * 2 + product_width + frame_width + 2,
                header_height + target_height + 2,
            ),
            (0, 255, 0),
            2,
        )
        return combined
