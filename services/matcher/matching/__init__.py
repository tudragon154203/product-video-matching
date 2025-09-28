"""Matching engine that coordinates search, scoring, and aggregation."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from common_py.logging_config import configure_logging

from matching_components.match_aggregator import MatchAggregator
from matching_components.pair_score_calculator import PairScoreCalculator
from matching_components.vector_searcher import VectorSearcher

logger = configure_logging("matcher:matching")


class MatchingEngine:
    """Core matching logic combining embedding and keypoint signals."""

    def __init__(self, db: Any, data_root: str, **params: Any) -> None:
        self.db = db
        self.data_root = Path(data_root)

        self.retrieval_topk = params.get("retrieval_topk", 20)
        self.sim_deep_min = params.get("sim_deep_min", 0.82)
        self.inliers_min = params.get("inliers_min", 0.35)
        self.match_best_min = params.get("match_best_min", 0.88)
        self.match_cons_min = params.get("match_cons_min", 2)
        self.match_accept = params.get("match_accept", 0.80)

        self.vector_searcher = VectorSearcher(db, self.retrieval_topk)
        self.pair_score_calculator = PairScoreCalculator(
            self.sim_deep_min,
            self.inliers_min,
        )
        self.match_aggregator = MatchAggregator(
            self.match_best_min,
            self.match_cons_min,
            self.match_accept,
        )

    async def initialize(self) -> None:
        """Initialise matching engine resources."""

        logger.info("Matching engine initialized")

    async def cleanup(self) -> None:
        """Clean up any allocated resources."""

        return None

    async def match_product_video(
        self,
        product_id: str,
        video_id: str,
        job_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Match a product against a video and return aggregate results."""

        try:
            product_images = await self.get_product_images(product_id)
            if not product_images:
                logger.warning(
                    "No images found for product",
                    product_id=product_id,
                )
                return None

            video_frames = await self.get_video_frames(video_id)
            if not video_frames:
                logger.warning(
                    "No frames found for video",
                    video_id=video_id,
                )
                return None

            logger.info(
                "Matching product vs video",
                product_id=product_id,
                video_id=video_id,
                image_count=len(product_images),
                frame_count=len(video_frames),
            )

            best_matches: List[Dict[str, Any]] = []

            for image in product_images:
                retrieve_similar_frames = (
                    self.vector_searcher.retrieve_similar_frames
                )
                similar_frames = await retrieve_similar_frames(
                    image,
                    video_frames,
                )

                for frame in similar_frames:
                    calculate_pair_score = (
                        self.pair_score_calculator.calculate_pair_score
                    )
                    pair_score = await calculate_pair_score(
                        image,
                        frame,
                    )

                    if pair_score < self.sim_deep_min:
                        continue

                    best_matches.append(
                        {
                            "img_id": image["img_id"],
                            "frame_id": frame["frame_id"],
                            "ts": frame["ts"],
                            "pair_score": pair_score,
                        }
                    )

            if not best_matches:
                logger.info(
                    "No matches found above threshold",
                    product_id=product_id,
                    video_id=video_id,
                )
                return None

            return await self.match_aggregator.aggregate_matches(
                best_matches,
                product_id,
                video_id,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to match product vs video",
                product_id=product_id,
                video_id=video_id,
                error=str(exc),
            )
            return None

    async def get_product_images(
        self,
        product_id: str,
    ) -> List[Dict[str, Any]]:
        """Fetch all images for a product."""

        query = """
        SELECT img_id, local_path, emb_rgb, emb_gray, kp_blob_path
        FROM product_images
        WHERE product_id = $1 AND emb_rgb IS NOT NULL
        """
        return await self.db.fetch_all(query, product_id)

    async def get_video_frames(
        self,
        video_id: str,
    ) -> List[Dict[str, Any]]:
        """Fetch all frames for a video."""

        query = """
        SELECT frame_id, ts, local_path, emb_rgb, emb_gray, kp_blob_path
        FROM video_frames
        WHERE video_id = $1 AND emb_rgb IS NOT NULL
        ORDER BY ts
        """
        return await self.db.fetch_all(query, video_id)
