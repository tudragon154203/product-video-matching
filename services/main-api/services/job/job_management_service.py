import uuid
import json
import time
from typing import Dict, Any
from fastapi import HTTPException
from common_py.logging_config import configure_logging
from config_loader import config
from models.schemas import StartJobRequest, StartJobResponse, JobStatusResponse
from services.llm.llm_service import LLMService
from services.llm.prompt_service import PromptService
from handlers.database_handler import DatabaseHandler
from handlers.broker_handler import BrokerHandler
from .job_initializer import JobInitializer

logger = configure_logging("main-api")

class JobManagementService:
    def __init__(self, db_handler: DatabaseHandler, broker_handler: BrokerHandler):
        self.db_handler = db_handler
        self.broker_handler = broker_handler
        self.llm_service = LLMService()
        self.prompt_service = PromptService()
        self.job_initializer = JobInitializer(db_handler, broker_handler, self.llm_service, self.prompt_service)

    async def start_job(self, request: StartJobRequest) -> StartJobResponse:
        try:
            job_id = str(uuid.uuid4())
            
            await self.job_initializer.initialize_job(job_id, request)
            
            logger.info(f"Started job (job_id: {job_id})")
            return StartJobResponse(job_id=job_id, status="started")
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e) if str(e) else 'Unknown error'}"
            logger.error(f"Failed to start job: {error_msg} (exception_type: {type(e).__name__})")
            import traceback
            logger.error(f"Exception traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=error_msg)

    async def get_job(self, job_id: str):
        """Get a complete job record by ID."""
        try:
            logger.info(f"Attempting to get job for job_id: {job_id}")
            job = await self.db_handler.get_job(job_id)
            logger.info(f"Result of db_handler.get_job for {job_id}: {job}")
            
            if not job:
                return None
            
            return job
        except Exception as e:
            logger.error(f"Failed to get job (job_id: {job_id}, error: {str(e)})")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_job_status(self, job_id: str) -> JobStatusResponse:
        try:
            logger.info(f"Attempting to get job status for job_id: {job_id}")
            job = await self.db_handler.get_job(job_id)
            logger.info(f"Result of db_handler.get_job for {job_id}: {job}")
            
            if not job:
                return JobStatusResponse(
                    job_id=job_id,
                    phase="unknown",
                    percent=0.0,
                    counts={
                        "products": 0,
                        "videos": 0,
                        "images": 0,
                        "frames": 0
                    },
                    updated_at=None
                )
            
            phase_progress = {
                "collection": 20.0,
                "feature_extraction": 50.0,
                "matching": 80.0,
                "evidence": 90.0,
                "completed": 100.0,
                "failed": 0.0
            }
            
            # Get comprehensive counts including frames
            product_count, video_count, image_count, frame_count, match_count = await self.db_handler.get_job_counts_with_frames(job_id)
            updated_at = await self.db_handler.get_job_updated_at(job_id)
            
            return JobStatusResponse(
                job_id=job_id,
                phase=job["phase"],
                percent=phase_progress.get(job["phase"], 0.0),
                counts={
                    "products": product_count,
                    "videos": video_count,
                    "images": image_count,
                    "frames": frame_count
                },
                updated_at=updated_at
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get job status (job_id: {job_id}, error: {str(e)})")
            raise HTTPException(status_code=500, detail=str(e))

    async def list_jobs(self, limit: int = 50, offset: int = 0, status: str = None):
        """List jobs with pagination and optional status filtering.
        
        Args:
            limit: Maximum number of jobs to return (default: 50)
            offset: Number of jobs to skip for pagination (default: 0)
            status: Filter by job phase/status (e.g., 'completed', 'failed', 'in_progress')
        
        Returns:
            tuple: (list of jobs, total count)
        """
        try:
            return await self.db_handler.list_jobs(limit, offset, status)
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            raise HTTPException(status_code=500, detail=str(e))