import os
import uuid
import json
import time
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import sys
import httpx

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker

# Configure logging
logger = configure_logging("main-api")

# Load service-specific configuration
from config_loader import load_env, MainAPIConfig
config: MainAPIConfig = load_env()

# Set OLLAMA_HOST for the ollama client
os.environ["OLLAMA_HOST"] = config.ollama_host

# Global instances
db = DatabaseManager(os.getenv("POSTGRES_DSN", "postgresql://postgres:dev@localhost:5432/product_video_matching"))
broker = MessageBroker(os.getenv("BUS_BROKER", "amqp://guest:guest@localhost:5672/"))
app = FastAPI(title="Main API Service", version="1.0.0")

# Request/Response models
class StartJobRequest(BaseModel):
    query: str
    top_amz: int = config.default_top_amz
    top_ebay: int = config.default_top_ebay
    platforms: list = config.default_platforms
    recency_days: int = config.default_recency_days

class StartJobResponse(BaseModel):
    job_id: str
    status: str

class JobStatusResponse(BaseModel):
    job_id: str
    phase: str
    percent: float
    counts: dict


@app.on_event("startup")
async def startup():
    """Initialize connections on startup"""
    logger.info(f"Connecting to database with DSN: {POSTGRES_DSN}")
    await db.connect()
    await broker.connect()
    logger.info("Main API service started")


@app.on_event("shutdown")
async def shutdown():
    """Clean up connections on shutdown"""
    await db.disconnect()
    await broker.disconnect()
    logger.info("Main API service stopped")


@app.post("/start-job", response_model=StartJobResponse)
async def start_job(request: StartJobRequest):
    """Start a new matching job"""
    try:
        job_id = str(uuid.uuid4())
        
        # Create job record
        await db.execute(
            "INSERT INTO jobs (job_id, industry, phase) VALUES ($1, $2, $3)",
            job_id, request.industry, "collection"
        )
        
        # Create and start the flow
        flow = MatchingFlow(job_id, request, db, broker)
        
        # Run flow in background
        asyncio.create_task(flow.run())
        
        logger.info("Started job", job_id=job_id, industry=request.industry)
        
        return StartJobResponse(job_id=job_id, status="started")
        
    except Exception as e:
        logger.error("Failed to start job", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get status of a job"""
    try:
        # Get job from database
        job = await db.fetch_one(
            "SELECT * FROM jobs WHERE job_id = $1", job_id
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
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
        product_count = await db.fetch_val(
            "SELECT COUNT(*) FROM products WHERE job_id = $1", job_id
        ) or 0
        
        video_count = await db.fetch_val(
            "SELECT COUNT(*) FROM videos WHERE job_id = $1", job_id
        ) or 0
        
        match_count = await db.fetch_val(
            "SELECT COUNT(*) FROM matches WHERE job_id = $1", job_id
        ) or 0
        
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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "main-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)