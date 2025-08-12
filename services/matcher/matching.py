import httpx
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
import structlog
from pathlib import Path

logger = structlog.get_logger()


class MatchingEngine:
    """Core matching logic combining embeddings and keypoints"""
    
    def __init__(self, db, data_root: str, **params):
        self.db = db
        self.data_root = Path(data_root)
        self.client = None
        
        # Matching parameters
        self.retrieval_topk = params.get("retrieval_topk", 20)
        self.sim_deep_min = params.get("sim_deep_min", 0.82)
        self.inliers_min = params.get("inliers_min", 0.35)
        self.match_best_min = params.get("match_best_min", 0.88)
        self.match_cons_min = params.get("match_cons_min", 2)
        self.match_accept = params.get("match_accept", 0.80)
    
    async def initialize(self):
        """Initialize HTTP client"""
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info("Matching engine initialized")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.client:
            await self.client.aclose()
    
    async def match_product_video(self, product_id: str, video_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """Match a product against a video"""
        try:
            # Get product images
            product_images = await self.get_product_images(product_id)
            if not product_images:
                logger.warning("No images found for product", product_id=product_id)
                return None
            
            # Get video frames
            video_frames = await self.get_video_frames(video_id)
            if not video_frames:
                logger.warning("No frames found for video", video_id=video_id)
                return None
            
            logger.info("Matching product vs video", 
                       product_id=product_id, 
                       video_id=video_id,
                       image_count=len(product_images),
                       frame_count=len(video_frames))
            
            # Perform matching between all image-frame pairs
            best_matches = []
            
            for image in product_images:
                # Get similar frames using vector search
                similar_frames = await self.retrieve_similar_frames(image, video_frames)
                
                # Rerank using keypoint matching
                for frame in similar_frames:
                    pair_score = await self.calculate_pair_score(image, frame)
                    
                    if pair_score >= self.sim_deep_min:
                        best_matches.append({
                            "img_id": image["img_id"],
                            "frame_id": frame["frame_id"],
                            "ts": frame["ts"],
                            "pair_score": pair_score
                        })
            
            if not best_matches:
                logger.info("No matches found above threshold", 
                           product_id=product_id, video_id=video_id)
                return None
            
            # Aggregate matches at product-video level
            return await self.aggregate_matches(best_matches, product_id, video_id)
            
        except Exception as e:
            logger.error("Failed to match product vs video", 
                        product_id=product_id, video_id=video_id, error=str(e))
            return None
    
    async def get_product_images(self, product_id: str) -> List[Dict[str, Any]]:
        """Get all images for a product"""
        query = """
        SELECT img_id, local_path, emb_rgb, emb_gray, kp_blob_path
        FROM product_images
        WHERE product_id = $1 AND emb_rgb IS NOT NULL
        """
        return await self.db.fetch_all(query, product_id)
    
    async def get_video_frames(self, video_id: str) -> List[Dict[str, Any]]:
        """Get all frames for a video"""
        query = """
        SELECT frame_id, ts, local_path, emb_rgb, emb_gray, kp_blob_path
        FROM video_frames
        WHERE video_id = $1 AND emb_rgb IS NOT NULL
        ORDER BY ts
        """
        return await self.db.fetch_all(query, video_id)
    
    async def retrieve_similar_frames(self, image: Dict[str, Any], video_frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Retrieve similar frames using vector search (mock implementation)"""
        try:
            # For MVP, use mock retrieval based on embedding similarity
            # In production, this would call the vector index service
            
            if not image.get("emb_rgb"):
                return video_frames[:self.retrieval_topk]  # Return first N frames
            
            # Mock similarity calculation
            image_emb = np.array(image["emb_rgb"])
            similarities = []
            
            for frame in video_frames:
                if frame.get("emb_rgb"):
                    frame_emb = np.array(frame["emb_rgb"])
                    # Calculate cosine similarity
                    similarity = np.dot(image_emb, frame_emb) / (
                        np.linalg.norm(image_emb) * np.linalg.norm(frame_emb)
                    )
                    similarities.append((similarity, frame))
                else:
                    # Random similarity for frames without embeddings
                    similarities.append((np.random.uniform(0.5, 0.9), frame))
            
            # Sort by similarity and return top-k
            similarities.sort(key=lambda x: x[0], reverse=True)
            return [frame for _, frame in similarities[:self.retrieval_topk]]
            
        except Exception as e:
            logger.error("Failed to retrieve similar frames", error=str(e))
            return video_frames[:self.retrieval_topk]
    
    async def calculate_pair_score(self, image: Dict[str, Any], frame: Dict[str, Any]) -> float:
        """Calculate similarity score between an image-frame pair"""
        try:
            # Embedding similarity (35% weight)
            sim_deep = await self.calculate_embedding_similarity(image, frame)
            
            # Keypoint similarity (55% weight) - mock implementation
            sim_kp = await self.calculate_keypoint_similarity(image, frame)
            
            # Edge similarity (10% weight) - mock implementation
            sim_edge = np.random.uniform(0.6, 0.9)
            
            # Weighted combination
            pair_score = 0.35 * sim_deep + 0.55 * sim_kp + 0.10 * sim_edge
            
            logger.debug("Calculated pair score", 
                        img_id=image["img_id"],
                        frame_id=frame["frame_id"],
                        sim_deep=sim_deep,
                        sim_kp=sim_kp,
                        sim_edge=sim_edge,
                        pair_score=pair_score)
            
            return pair_score
            
        except Exception as e:
            logger.error("Failed to calculate pair score", error=str(e))
            return 0.0
    
    async def calculate_embedding_similarity(self, image: Dict[str, Any], frame: Dict[str, Any]) -> float:
        """Calculate embedding similarity between image and frame"""
        try:
            if not image.get("emb_rgb") or not frame.get("emb_rgb"):
                return np.random.uniform(0.7, 0.9)  # Mock similarity
            
            image_emb = np.array(image["emb_rgb"])
            frame_emb = np.array(frame["emb_rgb"])
            
            # Cosine similarity
            similarity = np.dot(image_emb, frame_emb) / (
                np.linalg.norm(image_emb) * np.linalg.norm(frame_emb)
            )
            
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            logger.error("Failed to calculate embedding similarity", error=str(e))
            return 0.0
    
    async def calculate_keypoint_similarity(self, image: Dict[str, Any], frame: Dict[str, Any]) -> float:
        """Calculate keypoint similarity using RANSAC (mock implementation)"""
        try:
            # For MVP, return mock keypoint similarity
            # In production, this would load keypoint files and perform RANSAC
            
            if not image.get("kp_blob_path") or not frame.get("kp_blob_path"):
                return np.random.uniform(0.3, 0.7)
            
            # Mock RANSAC inliers ratio
            mock_inliers_ratio = np.random.uniform(0.2, 0.8)
            
            # Apply minimum threshold
            if mock_inliers_ratio < self.inliers_min:
                return 0.0
            
            return mock_inliers_ratio
            
        except Exception as e:
            logger.error("Failed to calculate keypoint similarity", error=str(e))
            return 0.0
    
    async def aggregate_matches(self, best_matches: List[Dict[str, Any]], product_id: str, video_id: str) -> Optional[Dict[str, Any]]:
        """Aggregate pair matches to product-video level"""
        try:
            if not best_matches:
                return None
            
            # Sort by pair score
            best_matches.sort(key=lambda x: x["pair_score"], reverse=True)
            
            # Get best match
            best_match = best_matches[0]
            best_score = best_match["pair_score"]
            
            # Count consistency (pairs with score >= 0.80)
            consistency = sum(1 for match in best_matches if match["pair_score"] >= 0.80)
            
            # Apply acceptance rules
            accept = False
            if best_score >= self.match_best_min and consistency >= self.match_cons_min:
                accept = True
            elif best_score >= 0.92:  # High confidence threshold
                accept = True
            
            if not accept:
                logger.info("Match rejected by acceptance rules", 
                           product_id=product_id, 
                           video_id=video_id,
                           best_score=best_score,
                           consistency=consistency)
                return None
            
            # Calculate final score with bonuses
            final_score = best_score
            if consistency >= 3:
                final_score += 0.02  # Consistency bonus
            if len(set(match["img_id"] for match in best_matches)) >= 2:
                final_score += 0.02  # Coverage bonus
            
            # Check final acceptance threshold
            if final_score < self.match_accept:
                logger.info("Match rejected by final threshold", 
                           product_id=product_id, 
                           video_id=video_id,
                           final_score=final_score)
                return None
            
            return {
                "best_img_id": best_match["img_id"],
                "best_frame_id": best_match["frame_id"],
                "ts": best_match["ts"],
                "score": min(1.0, final_score),
                "best_pair_score": best_score,
                "consistency": consistency,
                "total_pairs": len(best_matches)
            }
            
        except Exception as e:
            logger.error("Failed to aggregate matches", error=str(e))
            return None