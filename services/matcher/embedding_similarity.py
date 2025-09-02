from common_py.logging_config import configure_logging
import numpy as np
from typing import Dict, Any, List, Tuple

logger = configure_logging("matcher:embedding_similarity")


class EmbeddingSimilarity:
    """
    Calculate similarity between image and video frame embeddings using CLIP and traditional CV features.
    
    Combines RGB and grayscale embeddings with configurable weights for robust matching.
    """
    
    def __init__(self, weights: Dict[str, float] = None):
        """
        Initialize with optional weights for RGB and grayscale embeddings
        
        Args:
            weights: Dict with 'rgb' and 'gray' keys (default: {'rgb': 0.7, 'gray': 0.3})
        """
        self.weights = weights or {'rgb': 0.7, 'gray': 0.3}
        if abs(sum(self.weights.values()) - 1.0) > 0.01:
            logger.warning("Weights should sum to 1.0, current sum: {}", sum(self.weights.values()))
    
    async def calculate_similarity(self, 
                                 image_embedding: Dict[str, Any], 
                                 frame_embedding: Dict[str, Any]) -> float:
        """
        Calculate weighted cosine similarity between image and frame embeddings
        
        Args:
            image_embedding: Dict containing 'emb_rgb' and 'emb_gray' arrays
            frame_embedding: Dict containing 'emb_rgb' and 'emb_gray' arrays
            
        Returns:
            float: Combined similarity score (0.0 to 1.0)
        """
        try:
            if not self._validate_embeddings(image_embedding, frame_embedding):
                logger.warning("Invalid embeddings provided", 
                             image_has_rgb=image_embedding.get('emb_rgb') is not None,
                             frame_has_rgb=frame_embedding.get('emb_rgb') is not None)
                return 0.0
            
            combined_score, rgb_similarity, gray_similarity = self._get_combined_score(image_embedding, frame_embedding)
            
            final_score = max(0.0, min(1.0, combined_score))
            
            logger.debug("Calculated embedding similarity",
                        rgb_similarity=rgb_similarity,
                        gray_similarity=gray_similarity,
                        combined_score=combined_score,
                        final_score=final_score)
            
            return final_score
            
        except Exception as e:
            logger.error("Failed to calculate embedding similarity", error=str(e))
            return 0.0

    def _get_combined_score(self, image_embedding: Dict[str, Any], frame_embedding: Dict[str, Any]) -> tuple[float, float, float]:
        rgb_similarity = self._calculate_cosine_similarity(
            image_embedding['emb_rgb'], 
            frame_embedding['emb_rgb']
        )
        
        gray_similarity = self._calculate_cosine_similarity(
            image_embedding['emb_gray'], 
            frame_embedding['emb_gray']
        )
        
        combined_score = (self.weights['rgb'] * rgb_similarity + 
                        self.weights['gray'] * gray_similarity)
        
        return combined_score, rgb_similarity, gray_similarity
    
    def _validate_embeddings(self, image_embedding: Dict[str, Any], 
                           frame_embedding: Dict[str, Any]) -> bool:
        """Validate that embeddings are present and valid"""
        return (isinstance(image_embedding, dict) and 
                isinstance(frame_embedding, dict) and
                image_embedding.get('emb_rgb') is not None and
                frame_embedding.get('emb_rgb') is not None)
    
    def _calculate_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            # Ensure vectors are numpy arrays
            vec1 = np.array(vec1, dtype=np.float32)
            vec2 = np.array(vec2, dtype=np.float32)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            logger.error("Failed to calculate cosine similarity", error=str(e))
            return 0.0
    
    async def batch_similarity_search(self,
                                   query_embedding: Dict[str, Any],
                                   candidate_embeddings: List[Dict[str, Any]],
                                   top_k: int = 20) -> List[Dict[str, Any]]:
        """
        Find top-k most similar embeddings from a list of candidates
        
        Args:
            query_embedding: Image embedding to compare against
            candidate_embeddings: List of frame embeddings to search through
            top_k: Number of top results to return
            
        Returns:
            List of dicts with 'frame_id', 'similarity', and original data
        """
        try:
            similarity_scores = []
            
            for candidate in candidate_embeddings:
                similarity = await self.calculate_similarity(query_embedding, candidate)
                if similarity > 0:
                    similarity_scores.append({
                        'frame_id': candidate.get('frame_id'),
                        'similarity': similarity,
                        'data': candidate
                    })
            
            # Sort by similarity (descending) and return top-k
            similarity_scores.sort(key=lambda x: x['similarity'], reverse=True)
            return similarity_scores[:top_k]
            
        except Exception as e:
            logger.error("Failed in batch similarity search", error=str(e))
            return []
    
    def get_embedding_stats(self, embeddings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about a set of embeddings"""
        try:
            rgb_similarities = []
            gray_similarities = []
            
            for emb in embeddings:
                if emb.get('emb_rgb') and emb.get('emb_gray'):
                    # Calculate self-similarity (should be 1.0)
                    rgb_sim = self._calculate_cosine_similarity(emb['emb_rgb'], emb['emb_rgb'])
                    gray_sim = self._calculate_cosine_similarity(emb['emb_gray'], emb['emb_gray'])
                    
                    rgb_similarities.append(rgb_sim)
                    gray_similarities.append(gray_sim)
            
            return {
                'count': len(embeddings),
                'rgb_self_similarity_mean': np.mean(rgb_similarities) if rgb_similarities else 0.0,
                'gray_self_similarity_mean': np.mean(gray_similarities) if gray_similarities else 0.0,
                'rgb_self_similarity_std': np.std(rgb_similarities) if rgb_similarities else 0.0,
                'gray_self_similarity_std': np.std(gray_similarities) if gray_similarities else 0.0
            }
            
        except Exception as e:
            logger.error("Failed to get embedding stats", error=str(e))
            return {'count': len(embeddings)}
