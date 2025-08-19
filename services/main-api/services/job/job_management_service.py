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

    async def get_job_status(self, job_id: str) -> JobStatusResponse:
        try:
            job = await self.db_handler.get_job(job_id)
            
            if not job:
                return JobStatusResponse(
                    job_id=job_id,
                    phase="unknown",
                    percent=0.0,
                    counts={
                        "products": 0,
                        "videos": 0,
                        "matches": 0
                    }
                )
            
            phase_progress = {
                "collection": 20.0,
                "feature_extraction": 50.0,
                "matching": 80.0,
                "evidence": 90.0,
                "completed": 100.0,
                "failed": 0.0
            }
            
            product_count, video_count, match_count = await self.db_handler.get_job_counts(job_id)
            
            return JobStatusResponse(
                job_id=job_id,
                phase=job["phase"],
                percent=phase_progress.get(job["phase"], 0.0),
                counts={
                    "products": product_count,
                    "videos": video_count,
                    "matches": match_count
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get job status (job_id: {job_id}, error: {str(e)})")
            raise HTTPException(status_code=500, detail=str(e))
