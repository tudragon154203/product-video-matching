"""Utilities for calculating embedding similarities."""

from typing import Any, Dict, List

import numpy as np

from common_py.logging_config import configure_logging

logger = configure_logging("matcher:embedding_similarity")


class EmbeddingSimilarity:
    """Compute similarity between image and video frame embeddings.

    Combines RGB and grayscale embeddings with configurable weights to
    provide robust scoring.
    """

    def __init__(self, weights: Dict[str, float] | None = None) -> None:
        """Initialise optional weights for RGB and grayscale embeddings."""

        self.weights = weights or {"rgb": 0.7, "gray": 0.3}
        if abs(sum(self.weights.values()) - 1.0) > 0.01:
            logger.warning(
                "Weights should sum to 1.0, current sum: {}",
                sum(self.weights.values()),
            )

    async def calculate_similarity(
        self,
        image_embedding: Dict[str, Any],
        frame_embedding: Dict[str, Any],
    ) -> float:
        """Calculate weighted cosine similarity for the provided embeddings."""

        try:
            if not self._validate_embeddings(image_embedding, frame_embedding):
                logger.warning(
                    "Invalid embeddings provided",
                    image_has_rgb=image_embedding.get("emb_rgb") is not None,
                    frame_has_rgb=frame_embedding.get("emb_rgb") is not None,
                )
                return 0.0

            combined_score, rgb_similarity, gray_similarity = (
                self._get_combined_score(image_embedding, frame_embedding)
            )

            final_score = max(0.0, min(1.0, combined_score))

            logger.debug(
                "Calculated embedding similarity",
                rgb_similarity=rgb_similarity,
                gray_similarity=gray_similarity,
                combined_score=combined_score,
                final_score=final_score,
            )

            return final_score
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to calculate embedding similarity",
                error=str(exc),
            )
            return 0.0

    def _get_combined_score(
        self,
        image_embedding: Dict[str, Any],
        frame_embedding: Dict[str, Any],
    ) -> tuple[float, float, float]:
        rgb_similarity = 0.0
        if (
            image_embedding.get("emb_rgb") is not None
            and frame_embedding.get("emb_rgb") is not None
        ):
            rgb_similarity = self._calculate_cosine_similarity(
                image_embedding["emb_rgb"],
                frame_embedding["emb_rgb"],
            )

        gray_similarity = 0.0
        if (
            image_embedding.get("emb_gray") is not None
            and frame_embedding.get("emb_gray") is not None
        ):
            gray_similarity = self._calculate_cosine_similarity(
                image_embedding["emb_gray"],
                frame_embedding["emb_gray"],
            )

        if gray_similarity > 0.0 and rgb_similarity > 0.0:
            combined_score = (
                self.weights["rgb"] * rgb_similarity
                + self.weights["gray"] * gray_similarity
            )
        elif gray_similarity > 0.0:
            combined_score = gray_similarity  # Only use grayscale if RGB not available
        else:
            combined_score = rgb_similarity  # Only use RGB if grayscale not available or 0

        return combined_score, rgb_similarity, gray_similarity

    def _validate_embeddings(
        self,
        image_embedding: Dict[str, Any],
        frame_embedding: Dict[str, Any],
    ) -> bool:
        """Validate that embeddings are present and of the expected shape."""

        return (
            isinstance(image_embedding, dict)
            and isinstance(frame_embedding, dict)
            and (
                (
                    image_embedding.get("emb_rgb") is not None
                    and frame_embedding.get("emb_rgb") is not None
                ) or (
                    image_embedding.get("emb_gray") is not None
                    and frame_embedding.get("emb_gray") is not None
                )
            )
        )

    def _calculate_cosine_similarity(
        self,
        vec1: np.ndarray,
        vec2: np.ndarray,
    ) -> float:
        """Calculate cosine similarity between two vectors."""

        try:
            vec1 = np.array(vec1, dtype=np.float32)
            vec2 = np.array(vec2, dtype=np.float32)

            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return max(0.0, min(1.0, similarity))
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to calculate cosine similarity",
                error=str(exc),
            )
            return 0.0

    async def batch_similarity_search(
        self,
        query_embedding: Dict[str, Any],
        candidate_embeddings: List[Dict[str, Any]],
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        """Find the top ``top_k`` most similar embeddings from candidates."""

        try:
            similarity_scores: List[Dict[str, Any]] = []

            for candidate in candidate_embeddings:
                similarity = await self.calculate_similarity(
                    query_embedding,
                    candidate,
                )
                if similarity > 0:
                    similarity_scores.append(
                        {
                            "frame_id": candidate.get("frame_id"),
                            "similarity": similarity,
                            "data": candidate,
                        }
                    )

            similarity_scores.sort(
                key=lambda record: record["similarity"],
                reverse=True,
            )
            return similarity_scores[:top_k]
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed in batch similarity search", error=str(exc))
            return []

    def get_embedding_stats(
        self,
        embeddings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Gather simple statistics for a collection of embeddings."""

        try:
            rgb_similarities: List[float] = []
            gray_similarities: List[float] = []

            for embedding in embeddings:
                if embedding.get("emb_rgb") and embedding.get("emb_gray"):
                    rgb_similarities.append(
                        self._calculate_cosine_similarity(
                            embedding["emb_rgb"],
                            embedding["emb_rgb"],
                        )
                    )
                    gray_similarities.append(
                        self._calculate_cosine_similarity(
                            embedding["emb_gray"],
                            embedding["emb_gray"],
                        )
                    )

            return {
                "count": len(embeddings),
                "rgb_self_similarity_mean": (
                    float(np.mean(rgb_similarities))
                    if rgb_similarities
                    else 0.0
                ),
                "gray_self_similarity_mean": (
                    float(np.mean(gray_similarities))
                    if gray_similarities
                    else 0.0
                ),
            }
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to gather embedding stats",
                error=str(exc),
            )
            return {"count": 0, "rgb_self_similarity_mean": 0.0, "gray_self_similarity_mean": 0.0}
