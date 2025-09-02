"""
Results API endpoint definitions for the Main API service.
Provides endpoints for product-video matching results.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path

from models.results_schemas import (
    MatchListResponse, MatchDetailResponse, StatsResponse, EvidenceResponse
)
from services.results.results_service import ResultsService
from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging
from api.dependency import get_db
from config_loader import config
from utils.image_utils import to_public_url

logger = configure_logging("main-api:results_endpoints")

router = APIRouter()

# Dependency function
def get_results_service(db: DatabaseManager = Depends(get_db)) -> ResultsService:
    return ResultsService(db)


@router.get(
    "/results",
    response_model=MatchListResponse,
    summary="Get matching results",
    description="Retrieve product-video matching results with optional filtering and pagination"
)
async def get_results(
    industry: Optional[str] = Query(None, description="Filter by industry"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum match score"),
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    results_service: ResultsService = Depends(get_results_service)
) -> MatchListResponse:
    """Get matching results with optional filtering and pagination"""
    try:
        results = await results_service.get_results(
            industry=industry,
            min_score=min_score,
            job_id=job_id,
            limit=limit,
            offset=offset
        )
        
        logger.info(
            f"Retrieved {len(results.items)} results",
            extra={
                "count": len(results.items),
                "total": results.total,
                "industry": industry,
                "min_score": min_score,
                "job_id": job_id,
                "limit": limit,
                "offset": offset
            }
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to get results: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/matches/{match_id}",
    response_model=MatchDetailResponse,
    summary="Get match details",
    description="Retrieve detailed information about a specific match"
)
async def get_match(
    match_id: str = Path(..., description="Match ID"),
    results_service: ResultsService = Depends(get_results_service)
) -> MatchDetailResponse:
    """Get detailed match information"""
    try:
        match = await results_service.get_match(match_id)
        
        if not match:
            raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
        
        logger.info(f"Retrieved match {match_id}")
        return match
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get match {match_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/evidence/{match_id}",
    response_model=EvidenceResponse,
    summary="Get evidence image",
    description="Get the evidence image path for a specific match"
)
async def get_evidence_image(
    match_id: str = Path(..., description="Match ID"),
    results_service: ResultsService = Depends(get_results_service)
) -> EvidenceResponse:
    """Get evidence image path for a match"""
    try:
        evidence_path = await results_service.get_evidence_path(match_id)
        
        if not evidence_path:
            raise HTTPException(status_code=404, detail=f"Evidence image for match {match_id} not found")
        
        logger.info(f"Retrieved evidence for match {match_id}")
        return EvidenceResponse(evidence_path=evidence_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get evidence for match {match_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get system statistics",
    description="Retrieve system-wide statistics and counts"
)
async def get_stats(
    results_service: ResultsService = Depends(get_results_service)
) -> StatsResponse:
    """Get system statistics"""
    try:
        stats = await results_service.get_stats()
        
        logger.info("Retrieved system statistics")
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
