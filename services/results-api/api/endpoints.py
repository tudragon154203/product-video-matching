"""
API endpoint definitions for the Results API service.
Clean separation of API route definitions from business logic.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
import logging

from core.dependencies import ResultsServiceDependency
from core.exceptions import ResourceNotFound, ValidationError
from schemas.requests import ResultsQueryParams
from schemas.responses import (
    MatchResponse,
    ProductResponse,
    VideoResponse,
    MatchDetailResponse,
    EvidenceResponse,
    StatsResponse,
    HealthResponse
)

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(
    prefix="",
    tags=["results"],
    responses={
        404: {"description": "Resource not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)


@router.get(
    "/results",
    response_model=List[MatchResponse],
    summary="Get matching results",
    description="Retrieve product-video matching results with optional filtering"
)
async def get_results(
    service: ResultsServiceDependency,
    industry: Optional[str] = Query(None, description="Filter by industry"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum match score"),
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
) -> List[MatchResponse]:
    """Get matching results with optional filtering"""
    try:
        results = await service.get_results(
            industry=industry,
            min_score=min_score,
            job_id=job_id,
            limit=limit,
            offset=offset
        )
        
        logger.info(
            f"Retrieved {len(results)} results",
            extra={
                "count": len(results),
                "industry": industry,
                "min_score": min_score,
                "job_id": job_id,
                "limit": limit,
                "offset": offset
            }
        )
        
        return [MatchResponse(**result) for result in results]
        
    except Exception as e:
        logger.error(f"Failed to get results: {e}")
        raise


@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Get product details",
    description="Retrieve detailed information about a specific product"
)
async def get_product(
    service: ResultsServiceDependency,
    product_id: str = Path(..., description="Product ID")
) -> ProductResponse:
    """Get detailed product information"""
    try:
        product = await service.get_product(product_id)
        
        if not product:
            raise ResourceNotFound("Product", product_id)
        
        logger.info(f"Retrieved product {product_id}")
        return ProductResponse(**product)
        
    except ResourceNotFound:
        raise
    except Exception as e:
        logger.error(f"Failed to get product {product_id}: {e}")
        raise


@router.get(
    "/videos/{video_id}",
    response_model=VideoResponse,
    summary="Get video details",
    description="Retrieve detailed information about a specific video"
)
async def get_video(
    service: ResultsServiceDependency,
    video_id: str = Path(..., description="Video ID")
) -> VideoResponse:
    """Get detailed video information"""
    try:
        video = await service.get_video(video_id)
        
        if not video:
            raise ResourceNotFound("Video", video_id)
        
        logger.info(f"Retrieved video {video_id}")
        return VideoResponse(**video)
        
    except ResourceNotFound:
        raise
    except Exception as e:
        logger.error(f"Failed to get video {video_id}: {e}")
        raise


@router.get(
    "/matches/{match_id}",
    response_model=MatchDetailResponse,
    summary="Get match details",
    description="Retrieve detailed information about a specific match"
)
async def get_match(
    service: ResultsServiceDependency,
    match_id: str = Path(..., description="Match ID")
) -> MatchDetailResponse:
    """Get detailed match information"""
    try:
        match = await service.get_match(match_id)
        
        if not match:
            raise ResourceNotFound("Match", match_id)
        
        logger.info(f"Retrieved match {match_id}")
        return MatchDetailResponse(**match)
        
    except ResourceNotFound:
        raise
    except Exception as e:
        logger.error(f"Failed to get match {match_id}: {e}")
        raise


@router.get(
    "/evidence/{match_id}",
    response_model=EvidenceResponse,
    summary="Get evidence image",
    description="Get the evidence image path for a specific match"
)
async def get_evidence_image(
    service: ResultsServiceDependency,
    match_id: str = Path(..., description="Match ID")
) -> EvidenceResponse:
    """Get evidence image path for a match"""
    try:
        evidence_path = await service.get_evidence_path(match_id)
        
        if not evidence_path:
            raise ResourceNotFound("Evidence image", match_id)
        
        logger.info(f"Retrieved evidence for match {match_id}")
        return EvidenceResponse(evidence_path=evidence_path)
        
    except ResourceNotFound:
        raise
    except Exception as e:
        logger.error(f"Failed to get evidence for match {match_id}: {e}")
        raise


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get system statistics",
    description="Retrieve system-wide statistics and counts"
)
async def get_stats(
    service: ResultsServiceDependency
) -> StatsResponse:
    """Get system statistics"""
    stats = await service.get_stats()
    
    logger.info("Retrieved system statistics")
    return StatsResponse(**stats)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health status of the service"
)
async def health_check() -> HealthResponse:
    """Simple health check endpoint"""
    try:
        # In a real implementation, this might check database connectivity
        # and other dependencies
        logger.debug("Health check requested")
        return HealthResponse(status="healthy")
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(status="unhealthy", message=str(e))