import uuid
import json
import time
import asyncio
import httpx
from typing import Dict, Any
from fastapi import HTTPException
from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from config_loader import config
from models.schemas import StartJobRequest, StartJobResponse, JobStatusResponse

# Configure logger
logger = configure_logging("main-api")

class JobService:
    def __init__(self, db: DatabaseManager, broker: MessageBroker):
        self.db = db
        self.broker = broker

    def build_cls_prompt(self, query: str, industry_labels: list) -> str:
        labels_csv = ",".join(industry_labels)
        return f"""Classify this query into one industry label from the list:

Query: {query}
Labels: {labels_csv}

Output only the label name, nothing else."""

    def build_gen_prompt(self, query: str, industry: str) -> str:
        return f"""Generate search queries in JSON format:

Input query: {query}
Industry: {industry}

Output JSON format:
{{
  "product": {{ "en": [queries] }},
  "video": {{ "vi": [queries], "zh": [queries] }}
}}

Rules:
- 2-4 English product queries
- 2-4 Vietnamese video queries
- 2-4 Chinese video queries
- Output only JSON, no additional text"""

    def normalize_queries(self, queries: Dict[str, Any], min_items: int = 2, max_items: int = 4) -> Dict[str, Any]:
        normalized = {
            "product": {"en": []},
            "video": {"vi": [], "zh": []}
        }
        
        if "product" in queries and "en" in queries["product"]:
            en_queries = queries["product"]["en"][:max_items]
            if len(en_queries) < min_items and len(en_queries) > 0:
                en_queries.extend([en_queries[0]] * (min_items - len(en_queries)))
            try:
                normalized["product"]["en"] = [q if isinstance(q, str) else str(q) for q in en_queries]
            except Exception:
                normalized["product"]["en"] = []
        
        if "video" in queries and "vi" in queries["video"]:
            vi_queries = queries["video"]["vi"][:max_items]
            if len(vi_queries) < min_items and len(vi_queries) > 0:
                vi_queries.extend([vi_queries[0]] * (min_items - len(vi_queries)))
            try:
                normalized["video"]["vi"] = [q if isinstance(q, str) else str(q) for q in vi_queries]
            except Exception:
                normalized["video"]["vi"] = []
        
        if "video" in queries and "zh" in queries["video"]:
            zh_queries = queries["video"]["zh"][:max_items]
            if len(zh_queries) < min_items and len(zh_queries) > 0:
                zh_queries.extend([zh_queries[0]] * (min_items - len(zh_queries)))
            try:
                normalized["video"]["zh"] = [q if isinstance(q, str) else str(q) for q in zh_queries]
            except Exception:
                normalized["video"]["zh"] = []
        
        return normalized

    def route_video_queries(self, queries: Dict[str, Any], platforms: list) -> Dict[str, list]:
        video_queries = {"vi": [], "zh": []}
        if "youtube" in platforms and "vi" in queries["video"]:
            video_queries["vi"] = queries["video"]["vi"]
        if "bilibili" in platforms and "zh" in queries["video"]:
            video_queries["zh"] = queries["video"]["zh"]
        return video_queries

    async def call_ollama(self, model: str, prompt: str, timeout_s: int, options: dict = None) -> dict:
        if options is None:
            options = {}
        
        options["timeout"] = timeout_s * 1000
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{config.OLLAMA_HOST}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": options
                    },
                    timeout=timeout_s
                )
                response.raise_for_status()
                return response.json()
            except UnicodeEncodeError as e:
                logger.error("Unicode encoding error in Ollama response", error=str(e))
                try:
                    text = response.text.encode('utf-8').decode('utf-8')
                    return json.loads(text)
                except Exception as inner_e:
                    logger.error("Failed to handle Unicode error", error=str(inner_e))
                    raise HTTPException(status_code=500, detail=f"Ollama request failed with encoding error: {str(e)}")
            except httpx.RequestError as e:
                logger.error("Ollama request failed", error=str(e))
                raise HTTPException(status_code=500, detail=f"Ollama request failed: {str(e)}")
            except httpx.HTTPStatusError as e:
                logger.error("Ollama request failed", status_code=e.response.status_code, error=e.response.text)
                raise HTTPException(status_code=500, detail=f"Ollama request failed: {e.response.text}")

    async def start_job(self, request: StartJobRequest) -> StartJobResponse:
        try:
            job_id = str(uuid.uuid4())
            query = request.query.strip()
            
            # Classify industry
            cls_prompt = self.build_cls_prompt(query, config.INDUSTRY_LABELS)
            t0 = time.time()
            try:
                cls_response = await self.call_ollama(
                    model=config.OLLAMA_MODEL_CLASSIFY,
                    prompt=cls_prompt,
                    timeout_s=config.OLLAMA_TIMEOUT
                )
                industry = cls_response["response"].strip()
                if industry not in config.INDUSTRY_LABELS:
                    industry = "other"
            finally:
                logger.info("ollama_classify_ms", ollama_classify_ms=(time.time()-t0)*1000)
            
            # Generate queries
            gen_prompt = self.build_gen_prompt(query, industry)
            t0 = time.time()
            try:
                gen_response = await self.call_ollama(
                    model=config.OLLAMA_MODEL_GENERATE,
                    prompt=gen_prompt,
                    timeout_s=config.OLLAMA_TIMEOUT,
                    options={"temperature": 0.2}
                )
                try:
                    queries = json.loads(gen_response["response"])
                    queries = self.normalize_queries(queries, min_items=2, max_items=4)
                except json.JSONDecodeError:
                    queries = {
                        "product": {"en": [query]},
                        "video": {"vi": [query], "zh": [query]}
                    }
            finally:
                logger.info("ollama_generate_ms", ollama_generate_ms=(time.time()-t0)*1000)
            
            # Store job in database
            try:
                await self.db.execute(
                    "INSERT INTO jobs (job_id, query, industry, queries, phase) VALUES ($1, $2, $3, $4, $5)",
                    job_id, query, industry, json.dumps(queries), "collection"
                )
            except Exception as e:
                logger.warning(f"Failed to store job in database: {e}")
            
            # Publish events
            try:
                # Product collection request
                await self.broker.publish_event(
                    "products.collect.request",
                    {
                        "job_id": job_id,
                        "top_amz": request.top_amz,
                        "top_ebay": request.top_ebay,
                        "queries": {
                            "en": queries["product"]["en"]  # Use generated queries
                        }
                    },
                    correlation_id=job_id
                )
                
                # Video search request
                video_queries = self.route_video_queries(queries, request.platforms)
                await self.broker.publish_event(
                    "videos.search.request",
                    {
                        "job_id": job_id,
                        "industry": industry,
                        "queries": video_queries,
                        "platforms": request.platforms,
                        "recency_days": request.recency_days,
                    },
                    correlation_id=job_id
                )
            except Exception as e:
                logger.warning(f"Failed to publish events: {e}")
            
            logger.info("Started job", job_id=job_id, industry=industry)
            return StartJobResponse(job_id=job_id, status="started")
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e) if str(e) else 'Unknown error'}"
            logger.error("Failed to start job", error=error_msg, exception_type=type(e).__name__)
            import traceback
            logger.error("Exception traceback", traceback=traceback.format_exc())
            raise HTTPException(status_code=500, detail=error_msg)

    async def get_job_status(self, job_id: str) -> JobStatusResponse:
        try:
            # Get job from database
            try:
                job = await self.db.fetch_one(
                    "SELECT * FROM jobs WHERE job_id = $1", job_id
                )
            except Exception as e:
                logger.warning(f"Failed to fetch job from database: {e}")
                job = None
            
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
            try:
                product_count = await self.db.fetch_val(
                    "SELECT COUNT(*) FROM products WHERE job_id = $1", job_id
                ) or 0
                
                video_count = await self.db.fetch_val(
                    "SELECT COUNT(*) FROM videos WHERE job_id = $1", job_id
                ) or 0
                
                match_count = await self.db.fetch_val(
                    "SELECT COUNT(*) FROM matches WHERE job_id = $1", job_id
                ) or 0
            except Exception as e:
                logger.warning(f"Failed to fetch counts from database: {e}")
                product_count = 0
                video_count = 0
                match_count = 0
            
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
            logger.error("Failed to get job status", job_id=job_id, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    async def update_job_phases(self):
        """Update job phases based on progress"""
        try:
            # Get all jobs that are not completed or failed
            jobs = await self.db.fetch_all(
                "SELECT job_id, phase FROM jobs WHERE phase NOT IN ('completed', 'failed')"
            )
            
            for job in jobs:
                job_id = job["job_id"]
                current_phase = job["phase"]
                
                # Get counts for this job
                product_count = await self.db.fetch_val(
                    "SELECT COUNT(*) FROM products WHERE job_id = $1", job_id
                ) or 0
                
                video_count = await self.db.fetch_val(
                    "SELECT COUNT(*) FROM videos WHERE job_id = $1", job_id
                ) or 0
                
                # Count products with features (embeddings or keypoints)
                products_with_features = await self.db.fetch_val(
                    "SELECT COUNT(DISTINCT product_id) FROM product_images WHERE product_id IN (SELECT product_id FROM products WHERE job_id = $1) AND (emb_rgb IS NOT NULL OR kp_blob_path IS NOT NULL)", 
                    job_id
                ) or 0
                
                # Count videos with features
                videos_with_features = await self.db.fetch_val(
                    "SELECT COUNT(DISTINCT video_id) FROM video_frames WHERE video_id IN (SELECT video_id FROM videos WHERE job_id = $1) AND (emb_rgb IS NOT NULL OR kp_blob_path IS NOT NULL)", 
                    job_id
                ) or 0
                
                match_count = await self.db.fetch_val(
                    "SELECT COUNT(*) FROM matches WHERE job_id = $1", job_id
                ) or 0
                
                # Determine new phase based on progress
                new_phase = current_phase
                
                if current_phase == "collection":
                    # Move to feature_extraction if we have products OR videos
                    if product_count > 0 or video_count > 0:
                        new_phase = "feature_extraction"
                
                elif current_phase == "feature_extraction":
                    # Move to matching if any products or videos have features
                    if products_with_features > 0 or videos_with_features > 0:
                        new_phase = "matching"
                        
                        # Publish match request when transitioning to matching phase
                        try:
                            # Get industry from job record
                            job_record = await self.db.fetch_one(
                                "SELECT industry FROM jobs WHERE job_id = $1", job_id
                            )
                            industry = job_record["industry"] if job_record else "unknown"
                            
                            await self.broker.publish_event(
                                "match.request",
                                {
                                    "job_id": job_id,
                                    "industry": industry,
                                    "product_set_id": job_id,
                                    "video_set_id": job_id,
                                    "top_k": 20
                                },
                                correlation_id=job_id
                            )
                            logger.info("Published match request", job_id=job_id)
                        except Exception as e:
                            logger.error("Failed to publish match request", job_id=job_id, error=str(e))
                
                elif current_phase == "matching":
                    # Move to evidence if we have matches
                    if match_count > 0:
                        new_phase = "evidence"
                    # Or move to completed if no matches found after reasonable time
                    elif product_count > 0 and video_count > 0:
                        # Check if job is older than 5 minutes
                        job_age = await self.db.fetch_val(
                            "SELECT EXTRACT(EPOCH FROM (NOW() - created_at)) FROM jobs WHERE job_id = $1", 
                            job_id
                        )
                        if job_age and job_age > 300:  # 5 minutes
                            new_phase = "completed"
                
                elif current_phase == "evidence":
                    # Move to completed
                    new_phase = "completed"
                
                # Update phase if it changed
                if new_phase != current_phase:
                    await self.db.execute(
                        "UPDATE jobs SET phase = $1, updated_at = NOW() WHERE job_id = $2",
                        new_phase, job_id
                    )
                    logger.info("Updated job phase", job_id=job_id, 
                               old_phase=current_phase, new_phase=new_phase,
                               products=product_count, videos=video_count, 
                               products_with_features=products_with_features,
                               videos_with_features=videos_with_features,
                               matches=match_count)
                    
        except Exception as e:
            logger.error("Failed to update job phases", error=str(e))

    async def phase_update_task(self):
        """Background task to continuously update job phases"""
        while True:
            try:
                await self.update_job_phases()
                await asyncio.sleep(5)  # Update every 5 seconds
            except Exception as e:
                logger.error("Phase update task error", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error