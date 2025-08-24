import os
from fastapi import APIRouter, Depends, Query
from services.job.job_service import JobService
from models.schemas import StartJobRequest, StartJobResponse, JobStatusResponse, JobListResponse, JobItem
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from datetime import datetime


# Create router for job endpoints (no prefix)
router = APIRouter()

# Dependency functions
def get_db() -> DatabaseManager:
    return DatabaseManager(os.getenv("POSTGRES_DSN"))

def get_message_broker() -> MessageBroker:
    return MessageBroker(os.getenv("BUS_BROKER"))

def get_job_service(db: DatabaseManager = Depends(get_db), broker: MessageBroker = Depends(get_message_broker)) -> JobService:
    return JobService(db, broker)

@router.post("/start-job", response_model=StartJobResponse)
async def start_job(request: StartJobRequest, job_service: JobService = Depends(get_job_service)):
    """Start a new matching job"""
    return await job_service.start_job(request)

@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, job_service: JobService = Depends(get_job_service)):
    """Get status of a job"""
    return await job_service.get_job_status(job_id)


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of jobs to return"),
    offset: int = Query(0, ge=0, description="Number of jobs to skip for pagination"),
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