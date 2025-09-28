from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from datetime import datetime, timezone
import pytz

from models.schemas import (
    ImageListResponse,
    ImageItem
)
from services.job.job_service import JobService
from common_py.crud.product_image_crud import ProductImageCRUD
from common_py.logging_config import configure_logging
from api.dependency import get_product_image_crud, get_job_service
from config_loader import config

logger = configure_logging("main-api:image_endpoints")

router = APIRouter()

# Dependency functions use the centralized dependency module


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
    product_id: Optional[str] = Query(
        None, description="Filter by product ID"),
    q: Optional[str] = Query(
        None, description="Search query for product titles and image IDs"),
    limit: int = Query(
        10, ge=1, le=1000,
        description="Maximum number of items to return"
    ),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    sort_by: str = Query(
        "created_at", pattern="^(img_id|created_at)$", description="Field to sort by"),
    order: str = Query(
        "DESC", pattern="^(ASC|DESC)$",
        description="Sort order"
    ),
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
        sort_by: Field to sort by (img_id, created_at)
        order: Sort order (ASC or DESC)

    Returns:
        ImageListResponse: Paginated list of images matching the criteria
    """
    try:
        # Validate job exists
        job_status = await job_service.get_job_status(job_id)

        # If job_status.phase is "unknown", it means the job was not found in the database
        if job_status.phase == "unknown":
            raise HTTPException(
                status_code=404, detail=f"Job {job_id} not found"
            )

        # job variable was assigned but never used - removing it

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
            # Generate full URL for the image (API route based)
            # Import locally to avoid circular dependency if any
            from utils.image_utils import to_public_url
            public_url = to_public_url(
                image.local_path, config.DATA_ROOT_CONTAINER)
            if public_url:
                public_url = f"{config.MAIN_API_URL}{public_url}"
            else:
                # Handle case where public_url cannot be generated (e.g., invalid path)
                logger.warning(
                    f"Could not generate public URL for local_path: {image.local_path}"
                )
                public_url = None  # Or a default placeholder URL

            image_item = ImageItem(
                img_id=image.img_id,
                product_id=image.product_id,
                local_path=image.local_path,
                url=public_url,  # Add public URL field
                # Get product_title from joined query
                product_title=getattr(image, 'product_title', ''),
                updated_at=get_gmt7_time(image.created_at)
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
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )
