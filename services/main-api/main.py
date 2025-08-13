import os
import sys
from fastapi import FastAPI, HTTPException

# Add the app directory to the Python path
sys.path.append("/app/app")

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker

# Configure logging
logger = configure_logging("main-api")

# Load service-specific configuration
from config_loader import config

# Import services
from services.job_service import JobService

# Import models
from models.schemas import StartJobRequest, StartJobResponse, JobStatusResponse

# Import handlers
from handlers.lifecycle_handler import LifecycleHandler

# Import API endpoints
from api.job_endpoints import router as job_router
from api.health_endpoints import router as health_router

# Global instances
# Use configuration from the config object
db = DatabaseManager(config.POSTGRES_DSN)
broker = MessageBroker(config.BUS_BROKER)

# Initialize services
job_service = JobService(db, broker)

# Initialize lifecycle handler
lifecycle_handler = LifecycleHandler(db, broker, job_service)

app = FastAPI(title="Main API Service", version="1.0.0")

# Set the instances in the routers
import api.job_endpoints
import api.health_endpoints
api.job_endpoints.job_service_instance = job_service
api.health_endpoints.db_instance = db
api.health_endpoints.broker_instance = broker

# Include API routers
app.include_router(job_router)
app.include_router(health_router)

@app.on_event("startup")
async def startup():
    """Initialize connections on startup"""
    await lifecycle_handler.startup()

@app.on_event("shutdown")
async def shutdown():
    """Clean up connections on shutdown"""
    await lifecycle_handler.shutdown()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)