from fastapi import APIRouter, Depends, Query, HTTPException
from services.job.job_service import JobService
from models.schemas import StartJobRequest, StartJobResponse, JobStatusResponse, JobListResponse, JobItem
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
            updated_at=job["updated_at"]
        ))

    return JobListResponse(
        items=job_items,
        total=total,
        limit=limit,
        offset=offset
    )
