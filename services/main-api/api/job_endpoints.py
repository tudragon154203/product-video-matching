from fastapi import APIRouter
from services.job.job_service import JobService
from models.schemas import StartJobRequest, StartJobResponse, JobStatusResponse

# Create router for job endpoints (no prefix)
router = APIRouter()

# We'll set these when including the router in main.py
job_service_instance = None

@router.post("/start-job", response_model=StartJobResponse)
async def start_job(request: StartJobRequest):
    """Start a new matching job"""
    return await job_service_instance.start_job(request)

@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get status of a job"""
    return await job_service_instance.get_job_status(job_id)