import structlog
from typing import List, Dict, Any
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from vector_ops import VectorOperations

logger = structlog.get_logger()


class VectorIndexService:
    """Main service class for vector indexing"""
    
    def __init__(self, db: DatabaseManager, broker: MessageBroker):
        self.db = db
        self.broker = broker
        self.vector_ops = VectorOperations(db)
    
    async def handle_features_ready(self, event_data: Dict[str, Any]):
        """Handle features ready event for product images only"""
        try:
            entity_type = event_data["entity_type"]
            entity_id = event_data["id"]
            emb_rgb = event_data["emb_rgb"]
            emb_gray = event_data["emb_gray"]
            
            # Only index product images (not video frames)
            if entity_type == "product_image":
                logger.info("Indexing product image embeddings", image_id=entity_id)
                
                # Upsert embeddings into vector index
                await self.vector_ops.upsert_product_embeddings(entity_id, emb_rgb, emb_gray)
                
                logger.info("Indexed product image embeddings", image_id=entity_id)
            else:
                logger.debug("Skipping non-product entity", entity_type=entity_type, entity_id=entity_id)
                
        except Exception as e:
            logger.error("Failed to process features ready event", error=str(e))
            raise
    
    async def search_similar_products(self, query_vector: List[float], vector_type: str = "emb_rgb", top_k: int = 20) -> List[Dict[str, Any]]:
        """Search for similar product images using vector similarity"""
        try:
            if len(query_vector) != 512:
                raise ValueError("Query vector must be 512-dimensional")
            
            # Perform similarity search
            results = await self.vector_ops.search_similar_products(
                query_vector=query_vector,
                vector_type=vector_type,
                top_k=top_k
            )
            
            return results
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e) if str(e) else 'Unknown error'}"
            logger.error("Failed to perform similarity search", error=error_msg)
            raise
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector index"""
        try:
            stats = await self.vector_ops.get_index_stats()
            return stats
        except Exception as e:
            logger.error("Failed to get index stats", error=str(e))
            raise