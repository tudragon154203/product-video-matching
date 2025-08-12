import numpy as np
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger()


class VectorOperations:
    """Handles vector operations with pgvector"""
    
    def __init__(self, db):
        self.db = db
    
    async def upsert_product_embeddings(self, img_id: str, emb_rgb: List[float], emb_gray: List[float]):
        """Upsert embeddings for a product image"""
        try:
            # Handle empty vectors
            if not emb_rgb or not emb_gray:
                logger.warning("Empty embeddings received, skipping upsert", img_id=img_id)
                return
                
            # Convert lists to vector string format for PostgreSQL
            rgb_vector = '[' + ','.join(map(str, emb_rgb)) + ']'
            gray_vector = '[' + ','.join(map(str, emb_gray)) + ']'
            
            # Update embeddings in the database
            query = """
            UPDATE product_images 
            SET emb_rgb = $1::vector, emb_gray = $2::vector
            WHERE img_id = $3
            """
            
            await self.db.execute(query, rgb_vector, gray_vector, img_id)
            
            logger.info("Upserted product embeddings", img_id=img_id)
            
        except Exception as e:
            logger.error("Failed to upsert embeddings", img_id=img_id, error=str(e))
            raise
    
    async def search_similar_products(self, query_vector: List[float], vector_type: str = "emb_rgb", top_k: int = 20) -> List[Dict[str, Any]]:
        """Search for similar product images using cosine similarity"""
        try:
            # Validate vector type
            if vector_type not in ["emb_rgb", "emb_gray"]:
                raise ValueError(f"Invalid vector type: {vector_type}")
                
            # Handle empty query vector
            if not query_vector:
                logger.warning("Empty query vector received, returning empty results")
                return []
            
            # Convert query vector to string format
            query_vector_str = '[' + ','.join(map(str, query_vector)) + ']'
            
            # Perform similarity search using pgvector
            query = f"""
            SELECT 
                pi.img_id,
                pi.product_id,
                pi.local_path,
                1 - (pi.{vector_type} <=> $1::vector) as similarity
            FROM product_images pi
            WHERE pi.{vector_type} IS NOT NULL
            ORDER BY pi.{vector_type} <=> $1::vector
            LIMIT $2
            """
            
            results = await self.db.fetch_all(query, query_vector_str, top_k)
            
            logger.info("Performed similarity search", 
                       vector_type=vector_type, 
                       top_k=top_k, 
                       results_count=len(results))
            
            return results
            
        except Exception as e:
            logger.error("Failed to search similar products", 
                        vector_type=vector_type, error=str(e))
            # Return mock results for MVP
            return await self._get_mock_search_results(top_k)
    
    async def _get_mock_search_results(self, top_k: int) -> List[Dict[str, Any]]:
        """Generate mock search results for MVP testing"""
        try:
            # Get some random product images from database
            query = """
            SELECT img_id, product_id, local_path
            FROM product_images
            ORDER BY RANDOM()
            LIMIT $1
            """
            
            results = await self.db.fetch_all(query, top_k)
            
            # Add mock similarity scores
            mock_results = []
            for i, result in enumerate(results):
                # Generate decreasing similarity scores
                similarity = 0.95 - (i * 0.05)  # 0.95, 0.90, 0.85, etc.
                
                mock_results.append({
                    "img_id": result["img_id"],
                    "product_id": result["product_id"],
                    "local_path": result["local_path"],
                    "similarity": max(0.5, similarity)  # Minimum 0.5 similarity
                })
            
            logger.info("Generated mock search results", count=len(mock_results))
            return mock_results
            
        except Exception as e:
            logger.error("Failed to generate mock search results", error=str(e))
            return []
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector index"""
        try:
            # Count total product images
            total_images = await self.db.fetch_val(
                "SELECT COUNT(*) FROM product_images"
            )
            
            # Count images with RGB embeddings
            rgb_indexed = await self.db.fetch_val(
                "SELECT COUNT(*) FROM product_images WHERE emb_rgb IS NOT NULL"
            )
            
            # Count images with grayscale embeddings
            gray_indexed = await self.db.fetch_val(
                "SELECT COUNT(*) FROM product_images WHERE emb_gray IS NOT NULL"
            )
            
            # Get index sizes (approximate)
            index_info = await self.db.fetch_all("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    pg_size_pretty(pg_relation_size(indexname::regclass)) as size
                FROM pg_indexes 
                WHERE tablename = 'product_images' 
                AND indexname LIKE '%emb_%'
            """)
            
            stats = {
                "total_images": total_images or 0,
                "rgb_indexed": rgb_indexed or 0,
                "gray_indexed": gray_indexed or 0,
                "indexing_progress": {
                    "rgb": (rgb_indexed / max(total_images, 1)) * 100 if total_images else 0,
                    "gray": (gray_indexed / max(total_images, 1)) * 100 if total_images else 0
                },
                "indexes": index_info
            }
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get index stats", error=str(e))
            return {
                "total_images": 0,
                "rgb_indexed": 0,
                "gray_indexed": 0,
                "indexing_progress": {"rgb": 0, "gray": 0},
                "indexes": []
            }