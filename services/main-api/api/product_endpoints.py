from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional

from models.schemas import ProductListResponse
from services.job.job_service import JobService
from services.product.product_service import ProductService
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from api.dependency import get_db, get_broker, get_job_service
from common_py.logging_config import configure_logging

logger = configure_logging("main-api")

router = APIRouter()

# Dependency functions use the centralized dependency module

def get_product_service(db: DatabaseManager = Depends(get_db)) -> ProductService:
    return ProductService(db)


@router.get("/jobs/{job_id}/products", response_model=ProductListResponse)
async def get_job_products(
    job_id: str,
    q: Optional[str] = Query(None, description="Search query for product titles, brands, or ASIN/ItemID"),
    src: Optional[str] = Query(None, description="Filter by source (amazon, ebay)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    sort_by: str = Query("created_at", pattern="^(product_id|title|brand|src|created_at)$", description="Field to sort by"),
    order: str = Query("DESC", pattern="^(ASC|DESC)$", description="Sort order"),
    job_service: JobService = Depends(get_job_service),
    product_service: ProductService = Depends(get_product_service)
):
    """
    Get products for a specific job with filtering and pagination.
    
    Args:
        job_id: The job ID to filter products by
        q: Search query for product titles, brands, or ASIN/ItemID (case-insensitive)
        src: Filter by source platform (e.g., 'amazon', 'ebay')
        limit: Maximum number of items to return (1-1000)
        offset: Number of items to skip for pagination
        sort_by: Field to sort by (product_id, title, brand, src, created_at)
        order: Sort order (ASC or DESC)
    
    Returns:
        ProductListResponse: Paginated list of products matching the criteria
    """
    try:
        # Validate job exists
        job_status = await job_service.get_job_status(job_id)
        logger.info(f"Inside get_job_products: job_id={job_id}, job_status.phase={job_status.phase}")
        
        # If job_status.phase is "unknown", it means the job was not found in the database
        if job_status.phase == "unknown":
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Delegate to service
        return await product_service.get_job_products(
            job_id=job_id,
            search_query=q,
            src=src,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            order=order
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")