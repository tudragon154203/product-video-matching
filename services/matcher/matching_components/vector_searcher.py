"""Vector search utilities for retrieving candidate frames."""

from typing import Any, Dict, List

import numpy as np

from common_py.logging_config import configure_logging

logger = configure_logging("matcher:vector_searcher")


class VectorSearcher:
    """Perform vector searches and provide fallbacks when necessary."""

    def __init__(self, db: Any, retrieval_topk: int) -> None:
        self.db = db
        self.retrieval_topk = retrieval_topk

    async def retrieve_similar_frames(
        self,
        image: Dict[str, Any],
        video_frames: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Retrieve candidate frames using pgvector or a fallback."""

        try:
            if not image.get("emb_rgb"):
                return video_frames[: self.retrieval_topk]

            perform_vector_search = self._perform_vector_search
            return await perform_vector_search(image["emb_rgb"], video_frames)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to retrieve similar frames", error=str(exc))
            return await self._fallback_similarity_search(image, video_frames)

    async def _perform_vector_search(
        self,
        image_emb_data: List[float],
        video_frames: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        image_emb = np.array(image_emb_data, dtype=np.float32)

        await self._create_temp_embeddings_table(video_frames)
        vector_similarity_search = self._vector_similarity_search
        similar_frames = await vector_similarity_search(
            image_emb,
            video_frames,
        )

        return similar_frames[: self.retrieval_topk]

    async def _create_temp_embeddings_table(
        self,
        video_frames: List[Dict[str, Any]],
    ) -> None:
        """Create a temporary table for frame embeddings."""

        try:
            await self.db.execute("DROP TABLE IF EXISTS temp_video_embeddings")

            await self.db.execute(
                """
                CREATE TEMP TABLE temp_video_embeddings (
                    frame_id TEXT PRIMARY KEY,
                    emb_rgb FLOAT[],
                    emb_gray FLOAT[]
                )
                """
            )

            values_to_insert = []
            for frame in video_frames:
                if frame.get("emb_rgb"):
                    values_to_insert.append(
                        (frame["frame_id"], frame["emb_rgb"], frame.get("emb_gray"))
                    )

            if values_to_insert:
                await self.db.executemany(
                    """
                    INSERT INTO temp_video_embeddings (
                        frame_id,
                        emb_rgb,
                        emb_gray
                    )
                    VALUES ($1, $2, $3)
                    """,
                    values_to_insert,
                )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to create temp embeddings table",
                error=str(exc),
            )

    async def _vector_similarity_search(
        self,
        image_emb: np.ndarray,
        video_frames: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search using pgvector."""

        try:
            emb_array = list(image_emb)

            query = """
                SELECT v.frame_id, 1 - (v.emb_rgb <=> $1) AS similarity
                FROM temp_video_embeddings v
                WHERE v.emb_rgb IS NOT NULL
                ORDER BY v.emb_rgb <=> $1
                LIMIT $2
            """

            fetch_all = self.db.fetch_all
            results = await fetch_all(query, emb_array, self.retrieval_topk)

            frame_map = {frame["frame_id"]: frame for frame in video_frames}
            similar_frames: List[Dict[str, Any]] = []

            for result in results:
                frame = frame_map.get(result["frame_id"])
                if not frame:
                    continue

                frame["similarity"] = result["similarity"]
                similar_frames.append(frame)

            return similar_frames
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to perform vector similarity search",
                error=str(exc),
            )
            return await self._fallback_similarity_search(
                {"emb_rgb": emb_array},
                video_frames,
            )

    async def _fallback_similarity_search(
        self,
        image: Dict[str, Any],
        video_frames: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Fallback similarity search using numpy calculations."""

        try:
            image_emb = np.array(image["emb_rgb"], dtype=np.float32)
            scored_frames: List[tuple[float, Dict[str, Any]]] = []

            for frame in video_frames:
                if frame.get("emb_rgb"):
                    frame_emb = np.array(frame["emb_rgb"], dtype=np.float32)
                    similarity = np.dot(image_emb, frame_emb) / (
                        np.linalg.norm(image_emb) * np.linalg.norm(frame_emb)
                    )
                else:
                    logger.warning(
                        "Missing emb_rgb for frame, using default similarity in fallback search",
                        frame_id=frame.get("frame_id"),
                    )
                    similarity = 0.7  # Replaced random uniform with a fixed value

                frame["similarity"] = similarity
                scored_frames.append((similarity, frame))

            scored_frames.sort(key=lambda item: item[0], reverse=True)
            return [frame for _, frame in scored_frames]
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to perform fallback similarity search",
                error=str(exc),
            )
            return video_frames
