import os
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import sys
sys.path.append('/app/libs')

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from contracts.validator import validator
from vector_ops import VectorOperations

# Configure logging
logger = configure_logging("vector-index")

# Environment variables
sys.path.append('/app/infra')
from config import config

POSTGRES_DSN = config.POSTGRES_DSN
BUS_BROKER = config.BUS_BROKER

# Global instances
db = DatabaseManager(POSTGRES_DSN)
broker = MessageBroker(BUS_BROKER)
vector_ops = VectorOperations(db)
app = FastAPI(title="Vector Index Service", version="1.0.0")

# Request/Response models
class SearchRequest(BaseModel):
    query_vector: List[float]
    vector_type: str = "emb_rgb"  # or "emb_gray"
    top_k: int = 20

class SearchResult(BaseModel):
    img_id: str
    product_id: str
    similarity: float
    local_path: str

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_found: int


async def handle_features_ready(event_data):
    """Handle features ready event for product images only"""
    try:
        # Validate event
        validator.validate_event("features_ready", event_data)
        
        entity_type = event_data["entity_type"]
        entity_id = event_data["id"]
        emb_rgb = event_data["emb_rgb"]
        emb_gray = event_data["emb_gray"]
        
        # Only index product images (not video frames)
        if entity_type == "product_image":
            logger.info("Indexing product image embeddings", image_id=entity_id)
            
            # Upsert embeddings into vector index
            await vector_ops.upsert_product_embeddings(entity_id, emb_rgb, emb_gray)
            
            logger.info("Indexed product image embeddings", image_id=entity_id)
        else:
            logger.debug("Skipping non-product entity", entity_type=entity_type, entity_id=entity_id)
        
    except Exception as e:
        logger.error("Failed to process features ready event", error=str(e))
        raise


@app.on_event("startup")
async def startup():
    """Initialize connections on startup"""
    await db.connect()
    await broker.connect()
    
    # Subscribe to features ready events
    await broker.subscribe_to_topic(
        "features.ready",
        handle_features_ready
    )
    
    logger.info("Vector index service started")


@app.on_event("shutdown")
async def shutdown():
    """Clean up connections on shutdown"""
    await db.disconnect()
    await broker.disconnect()
    logger.info("Vector index service stopped")


@app.post("/search", response_model=SearchResponse)
async def search_similar(request: SearchRequest):
    """Search for similar product images using vector similarity"""
    try:
        if len(request.query_vector) != 512:
            raise HTTPException(status_code=400, detail="Query vector must be 512-dimensional")
        
        # Perform similarity search
        results = await vector_ops.search_similar_products(
            query_vector=request.query_vector,
            vector_type=request.vector_type,
            top_k=request.top_k
        )
        
        # Debug logging
        logger.info("Search results", count=len(results), results=results)
        
        # Format results
        search_results = []
        for result in results:
            logger.info("Processing result", result=result)
            search_results.append(SearchResult(
                img_id=result["img_id"],
                product_id=result["product_id"],
                similarity=result["similarity"],
                local_path=result["local_path"]
            ))
        
        return SearchResponse(
            results=search_results,
            total_found=len(search_results)
        )
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e) if str(e) else 'Unknown error'}"
        logger.error("Failed to perform similarity search", error=error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/stats")
async def get_index_stats():
    """Get statistics about the vector index"""
    try:
        stats = await vector_ops.get_index_stats()
        return stats
    except Exception as e:
        logger.error("Failed to get index stats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "vector-index"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)