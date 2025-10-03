import asyncio
import logging
from typing import List, Optional
from urllib.request import urlopen
import numpy as np
import cv2
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel

from .data_models import Product, VideoFrame, MatchResult

# Initialize logger
logger = logging.getLogger(__name__)


class MatcherService:
    """
    Core service for matching products to video frames using a hybrid approach
    of deep learning embeddings (CLIP) and traditional computer vision (AKAZE/SIFT + RANSAC).
    """

    def __init__(self):
        # Initialize CLIP model and processor
        # Using a small, common model for demonstration.
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        # Initialize traditional CV feature detector
        self.akaze = cv2.AKAZE_create()
        self.bf_matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        logger.info("MatcherService initialized with CLIP and AKAZE.")

    async def _load_image_from_url(self, url: str) -> Optional[Image.Image]:
        """Loads an image from a URL using PIL asynchronously (T025)."""
        def blocking_load():
            with urlopen(url) as response:
                return Image.open(response).convert("RGB")

        try:
            return await asyncio.to_thread(blocking_load)
        except Exception as e:
            logger.error(f"Failed to load image from {url}: {e}")
            return None

    def _get_clip_embedding(self, image: Image.Image) -> np.ndarray:
        """Generates a CLIP embedding for the given image."""
        inputs = self.clip_processor(images=image, return_tensors="pt")
        with torch.no_grad():
            image_features = self.clip_model.get_image_features(**inputs)
        return image_features.cpu().numpy().flatten()

    def _perform_cv_match(self, product_image: Image.Image, frame_image: Image.Image) -> Optional[MatchResult]:
        """
        Performs traditional computer vision matching (AKAZE/SIFT + RANSAC).
        Returns a MatchResult if a robust match is found, otherwise None.
        """
        # Convert PIL images to OpenCV format (numpy array)
        product_cv = np.array(product_image)
        frame_cv = np.array(frame_image)
        product_cv = cv2.cvtColor(product_cv, cv2.COLOR_RGB2BGR)
        frame_cv = cv2.cvtColor(frame_cv, cv2.COLOR_RGB2BGR)

        # 1. Feature Detection and Description
        kp1, des1 = self.akaze.detectAndCompute(product_cv, None)
        kp2, des2 = self.akaze.detectAndCompute(frame_cv, None)

        if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
            logger.debug("Not enough keypoints for CV match.")
            return None

        # 2. Feature Matching
        matches = self.bf_matcher.knnMatch(des1, des2, k=2)

        # 3. Ratio Test (Lowe's ratio test)
        good_matches = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)

        if len(good_matches) < 4:
            logger.debug(f"Not enough good matches after ratio test: {len(good_matches)}")
            return None

        # 4. RANSAC for Homography and Bounding Box
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        # Find homography matrix H and mask
        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

        if H is None:
            logger.debug("RANSAC failed to find a homography.")
            return None

        # Calculate bounding box in the frame image
        h, w = product_cv.shape[:2]
        corners = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
        transformed_corners = cv2.perspectiveTransform(corners, H)

        # Extract bounding box coordinates [x_min, y_min, x_max, y_max]
        x_coords = transformed_corners[:, 0, 0]
        y_coords = transformed_corners[:, 0, 1]
        bounding_box = [
            float(np.min(x_coords)),
            float(np.min(y_coords)),
            float(np.max(x_coords)),
            float(np.max(y_coords))
        ]

        # Simple confidence/score calculation (e.g., based on inliers)
        inliers = np.sum(mask)
        confidence_level = inliers / len(good_matches)
        match_score = confidence_level * 0.8 + (len(good_matches) / len(matches)) * 0.2  # Placeholder heuristic

        return MatchResult(
            product_id="placeholder",  # Will be replaced in the main match method
            frame_id="placeholder",  # Will be replaced in the main match method
            match_score=match_score,
            bounding_box=bounding_box,
            confidence_level=confidence_level
        )

    def _perform_match_logic(self, product: Product, frame: VideoFrame,
                             product_image: Image.Image, frame_image: Image.Image) -> List[MatchResult]:
        """
        Contains the heavy, blocking CV/CLIP logic, extracted for asynchronous execution (T025).
        """
        # --- 1. CLIP Embedding Similarity Check (Initial Filter) ---
        # In a real system, product embeddings would be pre-calculated and stored in pgvector.
        # Here, we calculate both for a simple similarity check.
        try:
            product_embedding = self._get_clip_embedding(product_image)
            frame_embedding = self._get_clip_embedding(frame_image)

            # Simple cosine similarity (placeholder for pgvector query)
            similarity = np.dot(product_embedding, frame_embedding) / (
                np.linalg.norm(product_embedding) * np.linalg.norm(frame_embedding)
            )
            logger.debug(f"CLIP Similarity: {similarity}")

            # Threshold for proceeding to CV match
            if similarity < 0.5:  # Arbitrary threshold
                logger.info("CLIP similarity too low. Skipping detailed CV match.")
                return []
        except Exception as e:
            logger.error(f"Error during CLIP processing: {e}")
            # For now, we'll return empty list to prevent unexpected behavior
            return []

        # --- 2. Traditional CV Match (High Precision Verification) ---
        cv_match_result = self._perform_cv_match(product_image, frame_image)

        if cv_match_result:
            # Finalize the MatchResult with correct IDs
            cv_match_result.product_id = product.product_id
            cv_match_result.frame_id = frame.frame_id

            # Combine CLIP similarity into the final score (e.g., weighted average)
            final_score = (cv_match_result.match_score * 0.7) + (similarity * 0.3)
            cv_match_result.match_score = final_score

            logger.info(f"Match found with final score: {final_score}")
            return [cv_match_result]
        else:
            logger.info("No robust CV match found.")
            return []

    async def match(self, product: Product, frame: VideoFrame) -> List[MatchResult]:
        """
        Performs the hybrid matching process between a product and a video frame.
        Offloads heavy computation to a thread pool to prevent blocking the event loop (T025).
        """
        logger.info(f"Starting match for product {product.product_id} and frame {frame.frame_id}")

        # Load images concurrently
        product_image, frame_image = await asyncio.gather(
            self._load_image_from_url(product.image_url),
            self._load_image_from_url(frame.image_url)
        )

        if not product_image or not frame_image:
            logger.warning("Skipping match due to failed image loading.")
            return []

        # Offload the heavy, blocking computation to a thread pool
        return await asyncio.to_thread(
            self._perform_match_logic,
            product,
            frame,
            product_image,
            frame_image
        )


# Export the service instance for use in handlers
matcher_service = MatcherService()
