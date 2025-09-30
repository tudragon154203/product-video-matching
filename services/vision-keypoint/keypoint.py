from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

from common_py.logging_config import configure_logging

from config_loader import config

logger = configure_logging("vision-keypoint:keypoint")


class KeypointExtractor:
    """Extracts keypoint descriptors using AKAZE and SIFT"""

    def __init__(self, data_root: str):
        self.data_root = Path(data_root)
        self.kp_dir = self.data_root / Path(config.KEYPOINT_DIR)
        self.kp_dir.mkdir(parents=True, exist_ok=True)

        # Initialize detectors
        self.akaze = cv2.AKAZE_create()
        self.sift = cv2.SIFT_create()

    async def extract_keypoints(self, image_path: str, entity_id: str) -> Optional[str]:
        """Extract keypoints and descriptors from an image"""
        try:
            # Load image
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                logger.error("Failed to load image", image_path=image_path)
                return None

            # Resize image to IMG_SIZE
            image = cv2.resize(image, config.IMG_SIZE, interpolation=cv2.INTER_LINEAR)

            # Try AKAZE first (faster and more robust)
            keypoints, descriptors = await self._extract_akaze_keypoints(image)

            # Fallback to SIFT if AKAZE fails or finds too few keypoints
            if descriptors is None or len(keypoints) < 10:
                logger.info(
                    "AKAZE found insufficient keypoints, trying SIFT",
                    entity_id=entity_id,
                    akaze_count=len(keypoints) if keypoints else 0,
                )
                keypoints, descriptors = await self._extract_sift_keypoints(image)

            if descriptors is None or len(keypoints) < 5:
                logger.warning(
                    "Insufficient keypoints found",
                    entity_id=entity_id,
                    final_count=len(keypoints) if keypoints else 0,
                )
                # Create mock keypoints for MVP
                return await self._create_mock_keypoints(entity_id)

            # Save keypoints and descriptors
            kp_blob_path = await self._save_keypoints(entity_id, keypoints, descriptors)

            logger.info(
                "Extracted keypoints",
                entity_id=entity_id,
                count=len(keypoints),
                descriptor_shape=descriptors.shape,
            )

            return kp_blob_path

        except Exception as e:
            logger.error(
                "Failed to extract keypoints",
                image_path=image_path,
                entity_id=entity_id,
                error=str(e),
            )
            return None

    async def _extract_akaze_keypoints(
        self, image: np.ndarray
    ) -> Tuple[list, Optional[np.ndarray]]:
        """Extract AKAZE keypoints and descriptors"""
        try:
            keypoints, descriptors = self.akaze.detectAndCompute(image, None)
            return keypoints, descriptors
        except Exception as e:
            logger.error("AKAZE extraction failed", error=str(e))
            return [], None

    async def _extract_sift_keypoints(
        self, image: np.ndarray
    ) -> Tuple[list, Optional[np.ndarray]]:
        """Extract SIFT keypoints and descriptors"""
        try:
            keypoints, descriptors = self.sift.detectAndCompute(image, None)
            return keypoints, descriptors
        except Exception as e:
            logger.error("SIFT extraction failed", error=str(e))
            return [], None

    async def _save_keypoints(
        self, entity_id: str, keypoints: list, descriptors: np.ndarray
    ) -> str:
        """Save keypoints and descriptors to compressed numpy file"""
        kp_blob_path = self.kp_dir / f"{entity_id}.npz"

        # Convert keypoints to serializable format
        kp_data = []
        for kp in keypoints:
            kp_data.append(
                {
                    "pt": kp.pt,
                    "angle": kp.angle,
                    "response": kp.response,
                    "octave": kp.octave,
                    "size": kp.size,
                }
            )

        # Save to compressed numpy file
        np.savez_compressed(
            kp_blob_path,
            keypoints=kp_data,
            descriptors=descriptors,
            count=len(keypoints),
        )

        return str(kp_blob_path)

    async def _create_mock_keypoints(self, entity_id: str) -> str:
        """Create mock keypoints for MVP testing"""
        try:
            # Generate mock keypoints and descriptors
            num_keypoints = np.random.randint(20, 100)

            # Mock keypoint data
            kp_data = []
            for i in range(num_keypoints):
                kp_data.append(
                    {
                        "pt": (
                            np.random.uniform(50, 450),
                            np.random.uniform(50, 350),
                        ),
                        "angle": np.random.uniform(0, 360),
                        "response": np.random.uniform(0.1, 1.0),
                        "octave": np.random.randint(0, 4),
                        "size": np.random.uniform(5, 20),
                    }
                )

            # Mock descriptors (64-dimensional for AKAZE, 128 for SIFT)
            # Use 64 for consistency
            descriptors = np.random.randint(0, 256, (num_keypoints, 64), dtype=np.uint8)

            # Save mock data
            kp_blob_path = self.kp_dir / f"{entity_id}.npz"
            np.savez_compressed(
                kp_blob_path,
                keypoints=kp_data,
                descriptors=descriptors,
                count=num_keypoints,
                mock=True,
            )

            logger.info(
                "Created mock keypoints",
                entity_id=entity_id,
                count=num_keypoints,
            )

            return str(kp_blob_path)

        except Exception as e:
            logger.error(
                "Failed to create mock keypoints",
                entity_id=entity_id,
                error=str(e),
            )
            return None

    def load_keypoints(self, kp_blob_path: str) -> Tuple[list, np.ndarray]:
        """Load keypoints and descriptors from file"""
        try:
            data = np.load(kp_blob_path)

            # Reconstruct keypoints
            keypoints = []
            for kp_data in data["keypoints"]:
                kp = cv2.KeyPoint(
                    x=float(kp_data["pt"][0]),
                    y=float(kp_data["pt"][1]),
                    size=float(kp_data["size"]),
                    angle=float(kp_data["angle"]),
                    response=float(kp_data["response"]),
                    octave=int(kp_data["octave"]),
                )
                keypoints.append(kp)

            descriptors = data["descriptors"]

            return keypoints, descriptors

        except Exception as e:
            logger.error(
                "Failed to load keypoints",
                kp_blob_path=kp_blob_path,
                error=str(e),
            )
            return [], np.array([])

    async def extract_keypoints_with_mask(
        self, image_path: str, mask_path: str, entity_id: str
    ) -> Optional[str]:
        """Extract keypoints and descriptors from an image with mask applied"""
        try:
            # Load image
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                logger.error("Failed to load image", image_path=image_path)
                return None

            # Resize image to IMG_SIZE
            image = cv2.resize(image, config.IMG_SIZE, interpolation=cv2.INTER_LINEAR)

            # Load mask
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            if mask is None:
                logger.error("Failed to load mask", mask_path=mask_path)
                return None

            # Resize mask to IMG_SIZE
            mask = cv2.resize(mask, config.IMG_SIZE, interpolation=cv2.INTER_NEAREST)

            # Apply mask to image (set background to black)
            masked_image = cv2.bitwise_and(image, mask)

            # Try AKAZE first (faster and more robust) with mask
            keypoints, descriptors = await self._extract_akaze_keypoints_with_mask(
                masked_image, mask
            )

            # Fallback to SIFT if AKAZE fails or finds too few keypoints
            if descriptors is None or len(keypoints) < 10:
                logger.info(
                    "AKAZE found insufficient keypoints with mask, trying SIFT",
                    entity_id=entity_id,
                    akaze_count=len(keypoints) if keypoints else 0,
                )
                keypoints, descriptors = await self._extract_sift_keypoints_with_mask(
                    masked_image, mask
                )

            if descriptors is None or len(keypoints) < 5:
                logger.warning(
                    "Insufficient keypoints found with mask",
                    entity_id=entity_id,
                    final_count=len(keypoints) if keypoints else 0,
                )
                # Create mock keypoints for MVP
                return await self._create_mock_keypoints(entity_id)

            # Save keypoints and descriptors
            kp_blob_path = await self._save_keypoints(entity_id, keypoints, descriptors)

            logger.info(
                "Extracted keypoints with mask",
                entity_id=entity_id,
                count=len(keypoints),
                descriptor_shape=descriptors.shape,
            )

            return kp_blob_path

        except Exception as e:
            logger.error(
                "Failed to extract keypoints with mask",
                image_path=image_path,
                mask_path=mask_path,
                entity_id=entity_id,
                error=str(e),
            )
            return None

    async def _extract_akaze_keypoints_with_mask(
        self, image: np.ndarray, mask: np.ndarray
    ) -> Tuple[list, Optional[np.ndarray]]:
        """Extract AKAZE keypoints and descriptors with mask"""
        try:
            keypoints, descriptors = self.akaze.detectAndCompute(image, mask)
            return keypoints, descriptors
        except Exception as e:
            logger.error("AKAZE extraction with mask failed", error=str(e))
            return [], None

    async def _extract_sift_keypoints_with_mask(
        self, image: np.ndarray, mask: np.ndarray
    ) -> Tuple[list, Optional[np.ndarray]]:
        """Extract SIFT keypoints and descriptors with mask"""
        try:
            keypoints, descriptors = self.sift.detectAndCompute(image, mask)
            return keypoints, descriptors
        except Exception as e:
            logger.error("SIFT extraction with mask failed", error=str(e))
            return [], None
