import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sys

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager

# Configure logging
logger = configure_logging("results-api")

# Environment variables
from config_loader import config

POSTGRES_DSN = config.POSTGRES_DSN
DATA_ROOT = config.DATA_ROOT

# Global instances
db = DatabaseManager(POSTGRES_DSN)
app = FastAPI(title="Results API", version="1.0.0")

# Import service after db initialization
from service import ResultsService
service = ResultsService(db)

# Response models
class MatchResult(BaseModel):
    match_id: str
    job_id: str
    product_id: str
    video_id: str
    best_img_id: str
    best_frame_id: str
    ts: Optional[float]
    score: float
    evidence_path: Optional[str]
    created_at: str
    
    # Enriched data
    product_title: Optional[str] = None
    video_title: Optional[str] = None
    video_platform: Optional[str] = None

class ProductDetail(BaseModel):
    product_id: str
    src: str
    asin_or_itemid: str
    title: Optional[str]
    brand: Optional[str]
    url: Optional[str]
    created_at: str
    image_count: int

class VideoDetail(BaseModel):
    video_id: str
    platform: str
    url: str
    title: Optional[str]
    duration_s: Optional[int]
    published_at: Optional[str]
    created_at: str
    frame_count: int

class MatchDetail(BaseModel):
    match_id: str
    job_id: str
    product: ProductDetail
    video: VideoDetail
    best_img_id: str
    best_frame_id: str
    ts: Optional[float]
    score: float
    evidence_path: Optional[str]
    created_at: str


@app.on_event("startup")
async def startup():
    """Initialize database connection on startup"""
    await db.connect()
    logger.info("Results API service started")


@app.on_event("shutdown")
async def shutdown():
    """Clean up database connection on shutdown"""
    await db.disconnect()
    logger.info("Results API service stopped")


@app.get("/results", response_model=List[MatchResult])
async def get_results(
    industry: Optional[str] = Query(None, description="Filter by industry"),
    min_score: Optional[float] = Query(None, description="Minimum match score"),
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Offset for pagination")
):
    """Get matching results with optional filtering"""
    try:
        results = await service.get_results(
            industry=industry,
            min_score=min_score,
            job_id=job_id,
            limit=limit,
            offset=offset
        )
        return results
    except Exception as e:
        logger.error("Failed to get results", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/products/{product_id}", response_model=ProductDetail)
async def get_product(product_id: str):
    """Get detailed product information"""
    try:
        product = await service.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get product", product_id=product_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/videos/{video_id}", response_model=VideoDetail)
async def get_video(video_id: str):
    """Get detailed video information"""
    try:
        video = await service.get_video(video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        return video
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get video", video_id=video_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/matches/{match_id}", response_model=MatchDetail)
async def get_match(match_id: str):
    """Get detailed match information"""
    try:
        match = await service.get_match(match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        return match
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get match", match_id=match_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/evidence/{match_id}")
async def get_evidence_image(match_id: str):
    """Serve evidence image for a match"""
    try:
        evidence_path = await service.get_evidence_path(match_id)
        if not evidence_path:
            raise HTTPException(status_code=404, detail="Evidence image not found")
        
        return FileResponse(
            evidence_path,
            media_type="image/jpeg",
            filename=f"evidence_{match_id}.jpg"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to serve evidence image", match_id=match_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        stats = await service.get_stats()
        return stats
    except Exception as e:
        logger.error("Failed to get stats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "results-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
