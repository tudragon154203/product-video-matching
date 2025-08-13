import os
import sys
import uuid
import json
import time
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import httpx

# Add the app directory to the Python path
sys.path.append("/app/app")

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker

# Configure logging
logger = configure_logging("main-api")

# Load service-specific configuration
from config_loader import config
# Set OLLAMA_HOST for the ollama client
os.environ["OLLAMA_HOST"] = config.OLLAMA_HOST

# Global instances
# Use configuration from the config object
postgres_dsn = config.POSTGRES_DSN
db = DatabaseManager(postgres_dsn)
broker = MessageBroker(config.BUS_BROKER)
app = FastAPI(title="Main API Service", version="1.0.0")

# Request/Response models
class StartJobRequest(BaseModel):
    query: str
    top_amz: int = config.DEFAULT_TOP_AMZ
    top_ebay: int = config.DEFAULT_TOP_EBAY
    platforms: list = config.DEFAULT_PLATFORMS
    recency_days: int = config.DEFAULT_RECENCY_DAYS

class StartJobResponse(BaseModel):
    job_id: str
    status: str

class JobStatusResponse(BaseModel):
    job_id: str
    phase: str
    percent: float
    counts: dict


async def phase_update_task():
    """Background task to update job phases"""
    while True:
        try:
            await update_job_phases()
            await asyncio.sleep(30)  # Update every 30 seconds
        except Exception as e:
            logger.error("Phase update task error", error=str(e))
            await asyncio.sleep(60)  # Wait longer on error


@app.on_event("startup")
async def startup():
    """Initialize connections on startup"""
    postgres_dsn = config.POSTGRES_DSN
    logger.info(f"Connecting to database with DSN: {postgres_dsn}")
    try:
        await db.connect()
    except Exception as e:
        logger.warning(f"Failed to connect to database: {e}. Continuing without database connection.")
    
    broker_url = config.BUS_BROKER
    logger.info(f"Connecting to message broker: {broker_url}")
    try:
        await broker.connect()
    except Exception as e:
        logger.warning(f"Failed to connect to message broker: {e}. Continuing without broker connection.")
    
    # Start background task for phase updates
    asyncio.create_task(phase_update_task())
    
    logger.info("Main API service started")


@app.on_event("shutdown")
async def shutdown():
    """Clean up connections on shutdown"""
    await db.disconnect()
    await broker.disconnect()
    logger.info("Main API service stopped")


def build_cls_prompt(query: str, industry_labels: list) -> str:
    """Build prompt for industry classification."""
    labels_csv = ",".join(industry_labels)
    return f"""Classify this query into one industry label from the list:

Query: {query}
Labels: {labels_csv}

Output only the label name, nothing else."""


def build_gen_prompt(query: str, industry: str) -> str:
    """Build prompt for query generation."""
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


def normalize_queries(queries: Dict[str, Any], min_items: int = 2, max_items: int = 4) -> Dict[str, Any]:
    """Normalize generated queries to ensure they meet requirements."""
    normalized = {
        "product": {"en": []},
        "video": {"vi": [], "zh": []}
    }
    
    # Normalize product.en queries
    if "product" in queries and "en" in queries["product"]:
        en_queries = queries["product"]["en"][:max_items]
        if len(en_queries) < min_items and len(en_queries) > 0:
            # Pad with existing queries
            en_queries.extend([en_queries[0]] * (min_items - len(en_queries)))
        # Handle encoding issues
        try:
            normalized["product"]["en"] = [q if isinstance(q, str) else str(q) for q in en_queries]
        except Exception:
            # Fallback to empty list if there are encoding issues
            normalized["product"]["en"] = []
    
    # Normalize video.vi queries
    if "video" in queries and "vi" in queries["video"]:
        vi_queries = queries["video"]["vi"][:max_items]
        if len(vi_queries) < min_items and len(vi_queries) > 0:
            # Pad with existing queries
            vi_queries.extend([vi_queries[0]] * (min_items - len(vi_queries)))
        # Handle encoding issues
        try:
            normalized["video"]["vi"] = [q if isinstance(q, str) else str(q) for q in vi_queries]
        except Exception:
            # Fallback to empty list if there are encoding issues
            normalized["video"]["vi"] = []
    
    # Normalize video.zh queries
    if "video" in queries and "zh" in queries["video"]:
        zh_queries = queries["video"]["zh"][:max_items]
        if len(zh_queries) < min_items and len(zh_queries) > 0:
            # Pad with existing queries
            zh_queries.extend([zh_queries[0]] * (min_items - len(zh_queries)))
        # Handle encoding issues
        try:
            normalized["video"]["zh"] = [q if isinstance(q, str) else str(q) for q in zh_queries]
        except Exception:
            # Fallback to empty list if there are encoding issues
            normalized["video"]["zh"] = []
    
    return normalized


def route_video_queries(queries: Dict[str, Any], platforms: list) -> Dict[str, list]:
    """Route video queries based on platforms."""
    video_queries = {}
    if "youtube" in platforms and "vi" in queries["video"]:
        video_queries["vi"] = queries["video"]["vi"]
    if "bilibili" in platforms and "zh" in queries["video"]:
        video_queries["zh"] = queries["video"]["zh"]
    return video_queries


async def call_ollama(model: str, prompt: str, timeout_s: int, options: dict = None) -> dict:
    """Call Ollama API."""
    if options is None:
        options = {}
    
    # Ensure timeout is in options
    options["timeout"] = timeout_s * 1000  # Convert to milliseconds
    
    # Use httpx to call Ollama API directly
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
            # Try to decode with error handling
            try:
                text = response.text.encode('utf-8').decode('utf-8')
                import json as json_module
                data = json_module.loads(text)
                return data
            except Exception as inner_e:
                logger.error("Failed to handle Unicode error", error=str(inner_e))
                raise HTTPException(status_code=500, detail=f"Ollama request failed with encoding error: {str(e)}")
        except httpx.RequestError as e:
            logger.error("Ollama request failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"Ollama request failed: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error("Ollama request failed", status_code=e.response.status_code, error=e.response.text)
            raise HTTPException(status_code=500, detail=f"Ollama request failed: {e.response.text}")


@app.post("/start-job", response_model=StartJobResponse)
async def start_job(request: StartJobRequest):
    """Start a new matching job"""
    try:
        job_id = str(uuid.uuid4())
        query = request.query.strip()
        
        # A) Classify industry using Ollama
        cls_prompt = build_cls_prompt(query, config.INDUSTRY_LABELS)
        t0 = time.time()
        try:
            cls_response = await call_ollama(
                model=config.OLLAMA_MODEL_CLASSIFY,
                prompt=cls_prompt,
                timeout_s=config.OLLAMA_TIMEOUT
            )
            industry = cls_response["response"].strip()
            if industry not in config.INDUSTRY_LABELS:
                industry = "other"
        finally:
            logger.info("ollama_classify_ms", ollama_classify_ms=(time.time()-t0)*1000)
        
        # B) Generate queries using Ollama
        gen_prompt = build_gen_prompt(query, industry)
        t0 = time.time()
        try:
            gen_response = await call_ollama(
                model=config.OLLAMA_MODEL_GENERATE,
                prompt=gen_prompt,
                timeout_s=config.OLLAMA_TIMEOUT,
                options={"temperature": 0.2}
            )
            try:
                queries = json.loads(gen_response["response"])
                queries = normalize_queries(queries, min_items=2, max_items=4)
            except json.JSONDecodeError:
                # Fallback to default queries if JSON parsing fails
                queries = {
                    "product": {"en": [query]},
                    "video": {"vi": [query], "zh": [query]}
                }
        finally:
            logger.info("ollama_generate_ms", ollama_generate_ms=(time.time()-t0)*1000)
        
        # C) Store job in database (if available)
        try:
            await db.execute(
                "INSERT INTO jobs (job_id, query, industry, queries, phase) VALUES ($1, $2, $3, $4, $5)",
                job_id, query, industry, json.dumps(queries), "collection"
            )
        except Exception as e:
            logger.warning(f"Failed to store job in database: {e}")
        
        # D) Publish events (if broker is available)
        try:
            # Publish product collection request
            await broker.publish_event(
                "products.collect.request",
                {
                    "job_id": job_id,
                    "industry": industry,
                    "top_amz": request.top_amz,
                    "top_ebay": request.top_ebay,
                },
                correlation_id=job_id
            )
            
            # Publish video search request
            video_queries = route_video_queries(queries, request.platforms)
            await broker.publish_event(
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


@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get status of a job"""
    try:
        # Get job from database (if available)
        try:
            job = await db.fetch_one(
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
        
        # Get counts from database (if available)
        try:
            product_count = await db.fetch_val(
                "SELECT COUNT(*) FROM products WHERE job_id = $1", job_id
            ) or 0
            
            video_count = await db.fetch_val(
                "SELECT COUNT(*) FROM videos WHERE job_id = $1", job_id
            ) or 0
            
            match_count = await db.fetch_val(
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


async def update_job_phases():
    """Update job phases based on progress"""
    try:
        # Get all jobs that are not completed or failed
        jobs = await db.fetch_all(
            "SELECT job_id, phase FROM jobs WHERE phase NOT IN ('completed', 'failed')"
        )
        
        for job in jobs:
            job_id = job["job_id"]
            current_phase = job["phase"]
            
            # Get counts for this job
            product_count = await db.fetch_val(
                "SELECT COUNT(*) FROM products WHERE job_id = $1", job_id
            ) or 0
            
            video_count = await db.fetch_val(
                "SELECT COUNT(*) FROM videos WHERE job_id = $1", job_id
            ) or 0
            
            # Count products with features (embeddings or keypoints)
            products_with_features = await db.fetch_val(
                "SELECT COUNT(DISTINCT product_id) FROM product_images WHERE product_id IN (SELECT product_id FROM products WHERE job_id = $1) AND (emb_rgb IS NOT NULL OR kp_blob_path IS NOT NULL)", 
                job_id
            ) or 0
            
            # Count videos with features
            videos_with_features = await db.fetch_val(
                "SELECT COUNT(DISTINCT video_id) FROM video_frames WHERE video_id IN (SELECT video_id FROM videos WHERE job_id = $1) AND (emb_rgb IS NOT NULL OR kp_blob_path IS NOT NULL)", 
                job_id
            ) or 0
            
            match_count = await db.fetch_val(
                "SELECT COUNT(*) FROM matches WHERE job_id = $1", job_id
            ) or 0
            
            # Determine new phase based on progress
            new_phase = current_phase
            
            if current_phase == "collection":
                # Move to feature_extraction if we have products and videos
                if product_count > 0 and video_count > 0:
                    new_phase = "feature_extraction"
            
            elif current_phase == "feature_extraction":
                # Move to matching if most products and videos have features
                if (products_with_features >= product_count * 0.8 and 
                    videos_with_features >= video_count * 0.8):
                    new_phase = "matching"
                    
                    # Publish match request when transitioning to matching phase
                    try:
                        await broker.publish_event(
                            "match.request",
                            {
                                "job_id": job_id,
                                "industry": "home_garden",  # TODO: get from job record
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
                    job_age = await db.fetch_val(
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
                await db.execute(
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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection (if available)
        db_status = "unavailable"
        try:
            await db.fetch_one("SELECT 1")
            db_status = "healthy"
        except Exception as e:
            logger.warning("Database health check failed", error=str(e))
            db_status = "unhealthy"
        
        # Check message broker connection (if available)
        broker_status = "unavailable"
        try:
            if broker.connection:
                broker_status = "healthy"
            else:
                broker_status = "unhealthy"
        except Exception as e:
            logger.warning("Broker health check failed", error=str(e))
            broker_status = "unhealthy"
        
        # Check Ollama connection (optional - don't fail if Ollama is not available)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{config.OLLAMA_HOST}/api/tags", timeout=5)
                response.raise_for_status()
                ollama_status = "healthy"
        except Exception as ollama_error:
            # Log the error but don't fail the health check
            logger.warning("Ollama health check failed", error=str(ollama_error))
            ollama_status = "unavailable"
        
        return {
            "status": "healthy", 
            "service": "main-api", 
            "ollama": ollama_status,
            "database": db_status,
            "broker": broker_status
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)