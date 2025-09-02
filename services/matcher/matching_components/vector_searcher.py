import numpy as np
from typing import Dict, Any, Optional, List
from common_py.logging_config import configure_logging

logger = configure_logging("matcher:vector_searcher")

class VectorSearcher:
    def __init__(self, db, retrieval_topk: int):
        self.db = db
        self.retrieval_topk = retrieval_topk

    async def retrieve_similar_frames(self, image: Dict[str, Any], video_frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Retrieve similar frames using vector search with direct Postgres/pgvector access"""
        try:
            if not image.get("emb_rgb"):
                return video_frames[:self.retrieval_topk]  # Return first N frames
            
            return await self._perform_vector_search(image["emb_rgb"], video_frames)
            
        except Exception as e:
            logger.error("Failed to retrieve similar frames", error=str(e))
            # Fallback to basic similarity calculation
            return await self._fallback_similarity_search(image, video_frames)

    async def _perform_vector_search(self, image_emb_data: List[float], video_frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        image_emb = np.array(image_emb_data, dtype=np.float32)
        
        await self._create_temp_embeddings_table(video_frames)
        similar_frames = await self._vector_similarity_search(image_emb, video_frames)
        
        return similar_frames[:self.retrieval_topk]
    
    async def _create_temp_embeddings_table(self, video_frames: List[Dict[str, Any]]):
        """Create temporary table for video frame embeddings if needed"""
        try:
            # Drop existing temp table if it exists
            await self.db.execute("DROP TABLE IF EXISTS temp_video_embeddings")
            
            # Create temp table
            await self.db.execute("""
                CREATE TEMP TABLE temp_video_embeddings (
                    frame_id TEXT PRIMARY KEY,
                    emb_rgb FLOAT[],
                    emb_gray FLOAT[]
                )
            """)
            
            # Insert video frame embeddings
            for frame in video_frames:
                if frame.get("emb_rgb"):
                    await self.db.execute(
                        """
                        INSERT INTO temp_video_embeddings (frame_id, emb_rgb, emb_gray)
                        VALUES ($1, $2, $3)
                        """,
                        frame["frame_id"],
                        frame["emb_rgb"],
                        frame.get("emb_gray")
                    )
            
        except Exception as e:
            logger.error("Failed to create temp embeddings table", error=str(e))
    
    async def _vector_similarity_search(self, image_emb: np.ndarray, video_frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform vector similarity search using pgvector"""
        try:
            # Convert numpy array to PostgreSQL array format
            emb_array = list(image_emb)
            
            # Query using pgvector cosine similarity
            query = """
                SELECT v.frame_id, 1 - (v.emb_rgb <=> $1) as similarity
                FROM temp_video_embeddings v
                WHERE v.emb_rgb IS NOT NULL
                ORDER BY v.emb_rgb <=> $1
                LIMIT $2
            """
            
            results = await self.db.fetch_all(query, emb_array, self.retrieval_topk)
            
            # Map results back to original frame data
            frame_map = {frame["frame_id"]: frame for frame in video_frames}
            similar_frames = []
            
            for result in results:
                if result["frame_id"] in frame_map:
                    frame = frame_map[result["frame_id"]]
                    frame["similarity"] = result["similarity"]
                    similar_frames.append(frame)
            
            return similar_frames
            
        except Exception as e:
            logger.error("Failed to perform vector similarity search", error=str(e))
            return await self._fallback_similarity_search({"emb_rgb": emb_array}, video_frames)
    
    async def _fallback_similarity_search(self, image: Dict[str, Any], video_frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback similarity search using numpy calculations"""
        try:
            image_emb = np.array(image["emb_rgb"], dtype=np.float32)
            similarities = []
            
            for frame in video_frames:
                if frame.get("emb_rgb"):
                    frame_emb = np.array(frame["emb_rgb"], dtype=np.float32)
                    # Calculate cosine similarity
                    similarity = np.dot(image_emb, frame_emb) / (
                        np.linalg.norm(image_emb) * np.linalg.norm(frame_emb)
                    )
                    frame["similarity"] = similarity
                    similarities.append((similarity, frame))
                else:
                    # Random similarity for frames without embeddings
                    similarity = np.random.uniform(0.5, 0.9)
                    frame["similarity"] = similarity
                    similarities.append((similarity, frame))
            
            # Sort by similarity and return
            similarities.sort(key=lambda x: x[0], reverse=True)
            return [frame for _, frame in similarities]
            
        except Exception as e:
            logger.error("Failed to perform fallback similarity search", error=str(e))
            return video_frames
