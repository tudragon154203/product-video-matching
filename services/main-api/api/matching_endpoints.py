from fastapi import APIRouter, Depends, HTTPException, Query
from api.dependency import get_db
from services.matching.matching_service import MatchingService
from models.matching_schemas import MatchingSummaryResponse
from common_py.logging_config import configure_logging

logger = configure_logging("main-api:matching_endpoints")

router = APIRouter(tags=["matching"])


@router.get(
    "/jobs/{job_id}/matching/summary",
    response_model=MatchingSummaryResponse
)
async def get_matching_summary(
    job_id: str,
    force_refresh: bool = Query(False),
    db=Depends(get_db)
):
    """
    Get matching phase summary for a job.
    
    Returns aggregated statistics about the matching process including:
    - Progress (candidates processed)
    - Match counts and scores
    - Evidence coverage
    - Health signals (queue depth, last event time)
    """
    service = MatchingService(db)
    summary = await service.get_matching_summary(job_id, force_refresh)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return summary
