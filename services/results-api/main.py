import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sys
sys.path.append('/app/libs')

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.crud import ProductCRUD, VideoCRUD, MatchCRUD
from common_py.models import Product, Video, Match

# Configure logging
logger = configure_logging("results-api")

# Environment variables
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:dev@postgres:5432/postgres")
DATA_ROOT = os.getenv("DATA_ROOT", "/app/data")

# Global instances
db = DatabaseManager(POSTGRES_DSN)
product_crud = ProductCRUD(db)
video_crud = VideoCRUD(db)
match_crud = MatchCRUD(db)
app = FastAPI(title="Results API", version="1.0.0")

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
        # Get matches
        matches = await match_crud.list_matches(
            job_id=job_id,
            min_score=min_score,
            limit=limit,
            offset=offset
        )
        
        # Enrich with product and video information
        enriched_matches = []
        for match in matches:
            # Get product info
            product = await product_crud.get_product(match.product_id)
            
            # Get video info
            video = await video_crud.get_video(match.video_id)
            
            # Filter by industry if specified
            if industry and product and industry.lower() not in (product.title or "").lower():
                continue
            
            enriched_match = MatchResult(
                match_id=match.match_id,
                job_id=match.job_id,
                product_id=match.product_id,
                video_id=match.video_id,
                best_img_id=match.best_img_id,
                best_frame_id=match.best_frame_id,
                ts=match.ts,
                score=match.score,
                evidence_path=match.evidence_path,
                created_at=match.created_at.isoformat() if match.created_at else "",
                product_title=product.title if product else None,
                video_title=video.title if video else None,
                video_platform=video.platform if video else None
            )
            
            enriched_matches.append(enriched_match)
        
        logger.info("Retrieved results", 
                   count=len(enriched_matches), 
                   industry=industry, 
                   min_score=min_score)
        
        return enriched_matches
        
    except Exception as e:
        logger.error("Failed to get results", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/products/{product_id}", response_model=ProductDetail)
async def get_product(product_id: str):
    """Get detailed product information"""
    try:
        product = await product_crud.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Get image count
        image_count = await db.fetch_val(
            "SELECT COUNT(*) FROM product_images WHERE product_id = $1",
            product_id
        ) or 0
        
        return ProductDetail(
            product_id=product.product_id,
            src=product.src,
            asin_or_itemid=product.asin_or_itemid,
            title=product.title,
            brand=product.brand,
            url=product.url,
            created_at=product.created_at.isoformat() if product.created_at else "",
            image_count=image_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get product", product_id=product_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/videos/{video_id}", response_model=VideoDetail)
async def get_video(video_id: str):
    """Get detailed video information"""
    try:
        video = await video_crud.get_video(video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Get frame count
        frame_count = await db.fetch_val(
            "SELECT COUNT(*) FROM video_frames WHERE video_id = $1",
            video_id
        ) or 0
        
        return VideoDetail(
            video_id=video.video_id,
            platform=video.platform,
            url=video.url,
            title=video.title,
            duration_s=video.duration_s,
            published_at=video.published_at.isoformat() if video.published_at else None,
            created_at=video.created_at.isoformat() if video.created_at else "",
            frame_count=frame_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get video", video_id=video_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/matches/{match_id}", response_model=MatchDetail)
async def get_match(match_id: str):
    """Get detailed match information"""
    try:
        match = await match_crud.get_match(match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        
        # Get product details
        product = await product_crud.get_product(match.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Get video details
        video = await video_crud.get_video(match.video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Get counts
        product_image_count = await db.fetch_val(
            "SELECT COUNT(*) FROM product_images WHERE product_id = $1",
            match.product_id
        ) or 0
        
        video_frame_count = await db.fetch_val(
            "SELECT COUNT(*) FROM video_frames WHERE video_id = $1",
            match.video_id
        ) or 0
        
        return MatchDetail(
            match_id=match.match_id,
            job_id=match.job_id,
            product=ProductDetail(
                product_id=product.product_id,
                src=product.src,
                asin_or_itemid=product.asin_or_itemid,
                title=product.title,
                brand=product.brand,
                url=product.url,
                created_at=product.created_at.isoformat() if product.created_at else "",
                image_count=product_image_count
            ),
            video=VideoDetail(
                video_id=video.video_id,
                platform=video.platform,
                url=video.url,
                title=video.title,
                duration_s=video.duration_s,
                published_at=video.published_at.isoformat() if video.published_at else None,
                created_at=video.created_at.isoformat() if video.created_at else "",
                frame_count=video_frame_count
            ),
            best_img_id=match.best_img_id,
            best_frame_id=match.best_frame_id,
            ts=match.ts,
            score=match.score,
            evidence_path=match.evidence_path,
            created_at=match.created_at.isoformat() if match.created_at else ""
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get match", match_id=match_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/evidence/{match_id}")
async def get_evidence_image(match_id: str):
    """Serve evidence image for a match"""
    try:
        match = await match_crud.get_match(match_id)
        if not match or not match.evidence_path:
            raise HTTPException(status_code=404, detail="Evidence image not found")
        
        # Check if file exists
        if not os.path.exists(match.evidence_path):
            raise HTTPException(status_code=404, detail="Evidence file not found on disk")
        
        return FileResponse(
            match.evidence_path,
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
        stats = {
            "products": await db.fetch_val("SELECT COUNT(*) FROM products") or 0,
            "product_images": await db.fetch_val("SELECT COUNT(*) FROM product_images") or 0,
            "videos": await db.fetch_val("SELECT COUNT(*) FROM videos") or 0,
            "video_frames": await db.fetch_val("SELECT COUNT(*) FROM video_frames") or 0,
            "matches": await db.fetch_val("SELECT COUNT(*) FROM matches") or 0,
            "jobs": await db.fetch_val("SELECT COUNT(*) FROM jobs") or 0
        }
        
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