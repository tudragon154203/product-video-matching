import os
from fastapi import APIRouter, Depends
from services.job.job_service import JobService
from models.schemas import StartJobRequest, StartJobResponse, JobStatusResponse
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker


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