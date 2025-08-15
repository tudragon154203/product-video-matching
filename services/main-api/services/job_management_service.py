import uuid
import json
import time
from typing import Dict, Any
from fastapi import HTTPException
from common_py.logging_config import configure_logging
from config_loader import config
from models.schemas import StartJobRequest, StartJobResponse, JobStatusResponse
from services.llm_service import LLMService
from services.prompt_service import PromptService
from handlers.database_handler import DatabaseHandler
from handlers.broker_handler import BrokerHandler

logger = configure_logging("main-api")

class JobManagementService:
    def __init__(self, db_handler: DatabaseHandler, broker_handler: BrokerHandler):
        self.db_handler = db_handler
        self.broker_handler = broker_handler
        self.llm_service = LLMService()
        self.prompt_service = PromptService()

    async def start_job(self, request: StartJobRequest) -> StartJobResponse:
        try:
            job_id = str(uuid.uuid4())
            query = request.query.strip()
            
            # Classify industry using LLM with fallback
            cls_prompt = self.prompt_service.build_cls_prompt(query, config.INDUSTRY_LABELS)
            t0 = time.time()
            try:
                cls_response = await self.llm_service.call_llm("classify", cls_prompt)
                industry = cls_response["response"].strip()
                if industry not in config.INDUSTRY_LABELS:
                    industry = "other"
            finally:
                logger.info(f"llm_classify_ms: {(time.time()-t0)*1000}")
            
            # Generate queries using LLM with fallback
            gen_prompt = self.prompt_service.build_gen_prompt(query, industry)
            t0 = time.time()
            try:
                gen_response = await self.llm_service.call_llm("generate", gen_prompt, options={"temperature": 0.2})
                try:
                    queries = json.loads(gen_response["response"])
                    queries = self.prompt_service.normalize_queries(queries, min_items=2, max_items=4)
                except json.JSONDecodeError:
                    queries = {
                        "product": {"en": [query]},
                        "video": {"vi": [query], "zh": [query]}
                    }
            finally:
                logger.info(f"llm_generate_ms: {(time.time()-t0)*1000}")
            
            # Store job in database
            try:
                await self.db_handler.store_job(job_id, query, industry, json.dumps(queries), "collection")
            except Exception as e:
                logger.warning(f"Failed to store job in database: {e}")
            
            # Publish events
            try:
                # Product collection request
                await self.broker_handler.publish_product_collection_request(
                    job_id, 
                    request.top_amz, 
                    request.top_ebay, 
                    {"en": queries["product"]["en"]}  # Use generated queries
                )
                
                # Video search request
                video_queries = self.prompt_service.route_video_queries(queries, request.platforms)
                await self.broker_handler.publish_video_search_request(
                    job_id, 
                    industry, 
                    video_queries, 
                    request.platforms, 
                    request.recency_days
                )
            except Exception as e:
                logger.warning(f"Failed to publish events: {e}")
            
            logger.info(f"Started job (job_id: {job_id}, industry: {industry})")
            return StartJobResponse(job_id=job_id, status="started")
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e) if str(e) else 'Unknown error'}"
            logger.error(f"Failed to start job: {error_msg} (exception_type: {type(e).__name__})")
            import traceback
            logger.error(f"Exception traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=error_msg)

    async def get_job_status(self, job_id: str) -> JobStatusResponse:
        try:
            # Get job from database
            job = await self.db_handler.get_job(job_id)
            
            if not job:
                # Return a default response if job not found or database not available
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
            
            # Calculate progress based on phase
            phase_progress = {
                "collection": 20.0,
                "feature_extraction": 50.0,
                "matching": 80.0,
                "evidence": 90.0,
                "completed": 100.0,
                "failed": 0.0
            }
            
            # Get counts from database
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