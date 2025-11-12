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

            # Convert image embedding to numpy array first
            image_emb = self._convert_embedding(image["emb_rgb"])
            perform_vector_search = self._perform_vector_search
            return await perform_vector_search(image_emb.tolist(), video_frames)
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
                    emb_rgb VECTOR(512),
                    emb_gray VECTOR(512)
                )
                """
            )

            values_to_insert = []
            for frame in video_frames:
                if frame.get("emb_rgb"):
                    # Convert embeddings to numpy arrays and then to vector strings for pgvector
                    rgb_emb = self._convert_embedding(frame["emb_rgb"]).tolist()
                    rgb_emb_str = f"[{','.join(str(x) for x in rgb_emb)}]"

                    gray_emb_str = None
                    if frame.get("emb_gray"):
                        gray_emb = self._convert_embedding(frame["emb_gray"]).tolist()
                        gray_emb_str = f"[{','.join(str(x) for x in gray_emb)}]"

                    values_to_insert.append(
                        (frame["frame_id"], rgb_emb_str, gray_emb_str)
                    )

            if values_to_insert:
                await self.db.executemany(
                    """
                    INSERT INTO temp_video_embeddings (
                        frame_id,
                        emb_rgb,
                        emb_gray
                    )
                    VALUES ($1, $2::vector, $3::vector)
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
            # Convert to pgvector format string
            emb_vector_str = f"[{','.join(str(x) for x in emb_array)}]"

            query = """
                SELECT v.frame_id, 1 - (v.emb_rgb <=> $1::vector) AS similarity
                FROM temp_video_embeddings v
                WHERE v.emb_rgb IS NOT NULL
                ORDER BY v.emb_rgb <=> $1::vector
                LIMIT $2
            """

            fetch_all = self.db.fetch_all
            results = await fetch_all(query, emb_vector_str, self.retrieval_topk)

            frame_map = {frame["frame_id"]: frame for frame in video_frames}
            similar_frames: List[Dict[str, Any]] = []

            for result in results:
                frame = frame_map.get(result["frame_id"])
                if not frame:
                    continue

                # Convert asyncpg Record to dict if needed
                frame_dict = dict(frame) if hasattr(frame, 'keys') else frame
                frame_dict["similarity"] = result["similarity"]
                similar_frames.append(frame_dict)

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

    def _convert_embedding(self, embedding: Any) -> np.ndarray:
        """Convert embedding from various formats to numpy array."""
        if isinstance(embedding, np.ndarray):
            return embedding.astype(np.float32)

        if isinstance(embedding, list):
            return np.array(embedding, dtype=np.float32)

        if isinstance(embedding, str):
            try:
                # Try to parse as Python literal first
                import ast
                parsed = ast.literal_eval(embedding)
                return np.array(parsed, dtype=np.float32)
            except (ValueError, SyntaxError):
                # Fallback: split by comma and convert to float
                try:
                    values = [float(x.strip()) for x in embedding.strip('[]').split(',') if x.strip()]
                    return np.array(values, dtype=np.float32)
                except (ValueError, TypeError) as e:
                    logger.error(f"Failed to convert embedding string to array: {embedding[:100]}...")
                    raise e

        raise ValueError(f"Unsupported embedding type: {type(embedding)}")

    async def _fallback_similarity_search(
        self,
        image: Dict[str, Any],
        video_frames: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Fallback similarity search using numpy calculations."""

        try:
            # Convert image embedding to numpy array
            image_emb = self._convert_embedding(image["emb_rgb"])
            scored_frames: List[tuple[float, Dict[str, Any]]] = []

            for frame in video_frames:
                # Convert asyncpg Record to mutable dict if needed
                frame_dict = dict(frame) if hasattr(frame, 'keys') else frame

                if frame_dict.get("emb_rgb"):
                    try:
                        # Convert frame embedding to numpy array
                        frame_emb = self._convert_embedding(frame_dict["emb_rgb"])
                        similarity = np.dot(image_emb, frame_emb) / (
                            np.linalg.norm(image_emb) * np.linalg.norm(frame_emb)
                        )
                    except Exception as emb_error:
                        logger.warning(
                            "Failed to process frame embedding, using default similarity",
                            frame_id=frame_dict.get("frame_id"),
                            error=str(emb_error)
                        )
                        similarity = 0.7
                else:
                    logger.warning(
                        "Missing emb_rgb for frame, using default similarity in fallback search",
                        frame_id=frame_dict.get("frame_id"),
                    )
                    similarity = 0.7

                # Convert embeddings in frame_dict to numpy arrays for similarity calculation
                frame_dict_rgb = frame_dict.get("emb_rgb")
                frame_dict_gray = frame_dict.get("emb_gray")

                # Convert string embeddings to numpy arrays for similarity calculation
                if isinstance(frame_dict_rgb, str):
                    try:
                        frame_dict_rgb = self._convert_embedding(frame_dict_rgb)
                    except (ValueError, TypeError):
                        frame_dict_rgb = np.array([0.7])  # Fallback default similarity
                if isinstance(frame_dict_gray, str):
                    try:
                        frame_dict_gray = self._convert_embedding(frame_dict_gray)
                    except (ValueError, TypeError):
                        frame_dict_gray = np.array([0.7])  # Fallback default similarity

                if frame_dict_rgb is not None and frame_dict_gray is not None:
                    similarity = np.dot(frame_dict_rgb, frame_dict_gray) / (
                        np.linalg.norm(frame_dict_rgb) * np.linalg.norm(frame_dict_gray)
                    )
                elif frame_dict_rgb is not None:
                    similarity = np.dot(frame_dict_rgb, frame_dict_rgb) / (
                        np.linalg.norm(frame_dict_rgb) * np.linalg.norm(frame_dict_rgb)
                    )
                elif frame_dict_gray is not None:
                    similarity = np.dot(frame_dict_gray, frame_dict_gray) / (
                        np.linalg.norm(frame_dict_gray) * np.linalg.norm(frame_dict_gray)
                    )
                else:
                    similarity = 0.7

                frame_dict["similarity"] = similarity
                scored_frames.append((similarity, frame_dict))

            scored_frames.sort(key=lambda item: item[0], reverse=True)
            return [frame for _, frame in scored_frames]
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to perform fallback similarity search",
                error=str(exc),
            )
            return video_frames
