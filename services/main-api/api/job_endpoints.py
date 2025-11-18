from fastapi import APIRouter, Depends, Query, HTTPException
from services.job.job_service import JobService
from models.schemas import (
    StartJobRequest, StartJobResponse, JobStatusResponse, JobListResponse, JobItem,
    CancelJobRequest, CancelJobResponse, DeleteJobResponse
)
from api.dependency import get_job_service


# Create router for job endpoints (no prefix)
router = APIRouter()

# Dependency functions use the centralized dependency module


@router.post("/start-job", response_model=StartJobResponse)
async def start_job(request: StartJobRequest, job_service: JobService = Depends(get_job_service)):
    """Start a new matching job"""
    return await job_service.start_job(request)


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, job_service: JobService = Depends(get_job_service)):
    """Get status of a job"""
    return await job_service.get_job_status(job_id)


@router.get("/jobs/{job_id}", response_model=JobItem)
async def get_job(job_id: str, job_service: JobService = Depends(get_job_service)):
    """Get a specific job by ID"""
    job = await job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobItem(
        job_id=job["job_id"],
        query=job["query"],
        industry=job["industry"],
        phase=job["phase"],
        created_at=job["created_at"],
        updated_at=job["updated_at"]
    )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    limit: int = Query(
        50, ge=1, le=100,
        description="Maximum number of jobs to return"
    ),
    offset: int = Query(
        0, ge=0, description="Number of jobs to skip for pagination"
    ),
    status: str = Query(None, description="Filter by job status (phase)"),
    job_service: JobService = Depends(get_job_service)
):
    """List past jobs with pagination and optional status filtering"""
    jobs, total = await job_service.list_jobs(limit=limit, offset=offset, status=status)

    # Convert database records to JobItem objects
    job_items = []
    for job in jobs:
        job_items.append(JobItem(
            job_id=job["job_id"],
            query=job["query"],
            industry=job["industry"],
            phase=job["phase"],
            created_at=job["created_at"],
            updated_at=job["updated_at"],
            cancelled_at=job.get("cancelled_at"),
            deleted_at=job.get("deleted_at")
        ))

    return JobListResponse(
        items=job_items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("/jobs/{job_id}/cancel", response_model=CancelJobResponse)
async def cancel_job(
    job_id: str,
    request: CancelJobRequest = CancelJobRequest(),
    job_service: JobService = Depends(get_job_service)
):
    """Cancel a running job and purge its queued messages"""
    result = await job_service.cancel_job(
        job_id=job_id,
        reason=request.reason,
        notes=request.notes,
        cancelled_by="api_user"
    )

    return CancelJobResponse(
        job_id=result["job_id"],
        phase=result["phase"],
        cancelled_at=result["cancelled_at"],
        reason=result["reason"],
        notes=result.get("notes")
    )


@router.delete("/jobs/{job_id}", response_model=DeleteJobResponse)
async def delete_job(
    job_id: str,
    force: bool = Query(False, description="Force delete even if job is active"),
    job_service: JobService = Depends(get_job_service)
):
    """Delete a job and all its associated data"""
    result = await job_service.delete_job(
        job_id=job_id,
        force=force,
        deleted_by="api_user"
    )

    return DeleteJobResponse(
        job_id=result["job_id"],
        status=result["status"],
        deleted_at=result["deleted_at"]
    )
