import os
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from datetime import datetime, timezone
import pytz

from models.schemas import (
    ImageListResponse, 
    ImageItem
)
from services.job.job_service import JobService
from common_py.crud.product_image_crud import ProductImageCRUD
from common_py.crud.product_crud import ProductCRUD
from common_py.database import DatabaseManager # Import DatabaseManager
from common_py.messaging import MessageBroker # Import MessageBroker

router = APIRouter()

# Dependency functions
def get_db() -> DatabaseManager:
    return DatabaseManager(os.getenv("POSTGRES_DSN"))

def get_message_broker() -> MessageBroker:
    return MessageBroker(os.getenv("BUS_BROKER"))

def get_job_service(db: DatabaseManager = Depends(get_db), broker: MessageBroker = Depends(get_message_broker)) -> JobService:
    return JobService(db, broker)

def get_product_image_crud(db: DatabaseManager = Depends(get_db)) -> ProductImageCRUD:
    return ProductImageCRUD(db)

def get_product_crud(db: DatabaseManager = Depends(get_db)) -> ProductCRUD:
    return ProductCRUD(db)


def get_gmt7_time(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert datetime to GMT+7 timezone"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(pytz.timezone('Asia/Saigon'))


@router.get("/jobs/{job_id}/images", response_model=ImageListResponse)
async def get_job_images(
    job_id: str,
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    q: Optional[str] = Query(None, description="Search query for product titles and image IDs"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    sort_by: str = Query("updated_at", pattern="^(img_id|updated_at)$", description="Field to sort by"),
    order: str = Query("DESC", pattern="^(ASC|DESC)$", description="Sort order"),
    job_service: JobService = Depends(get_job_service),
    product_image_crud: ProductImageCRUD = Depends(get_product_image_crud)
):
    """
    Get images for a specific job with filtering and pagination.
    
    Args:
        job_id: The job ID to filter images by
        product_id: Filter by product ID
        q: Search query for product titles and image IDs (case-insensitive)
        limit: Maximum number of items to return (1-1000)
        offset: Number of items to skip for pagination
        sort_by: Field to sort by (img_id, updated_at)
        order: Sort order (ASC or DESC)
    
    Returns:
        ImageListResponse: Paginated list of images matching the criteria
    """
    try:
        # Validate job exists
        job_status = await job_service.get_job_status(job_id)
        
        # If job_status.phase is "unknown", it means the job was not found in the database
        if job_status.phase == "unknown":
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job = {"job_id": job_status.job_id, "updated_at": job_status.updated_at, "phase": job_status.phase, "percent": job_status.percent, "counts": job_status.counts}
        
        # Get images with filtering and pagination
        images = await product_image_crud.list_product_images_by_job(
            job_id=job_id,
            product_id=product_id,
            search_query=q,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            order=order
        )
        
        # Get total count for pagination
        total = await product_image_crud.count_product_images_by_job(
            job_id=job_id,
            product_id=product_id,
            search_query=q
        )
        
        # Convert to response format and ensure datetime is in GMT+7
        image_items = []
        for image in images:
            image_item = ImageItem(
                img_id=image.img_id,
                product_id=image.product_id,
                local_path=image.local_path,
                product_title=getattr(image, 'product_title', ''),  # Get product_title from joined query
                updated_at=get_gmt7_time(image.updated_at or image.created_at)
            )
            image_items.append(image_item)
        
        return ImageListResponse(
            items=image_items,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")