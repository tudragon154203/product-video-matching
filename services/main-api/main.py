import sys
from fastapi import FastAPI

# Add the app directory to the Python path for bind mount setup
sys.path.append("/app/app")

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker

# Configure logging
logger = configure_logging("main-api")

# Load service-specific configuration
from config_loader import config

# Import services
from services.job.job_service import JobService

# Import handlers
from handlers.lifecycle_handler import LifecycleHandler

# Import API endpoints
from api.job_endpoints import router as job_router
from api.health_endpoints import router as health_router
from api.video_endpoints import router as video_router
from api.image_endpoints import router as image_router
from api.features_endpoints import router as features_router

# Global instances
# Use configuration from the config object
db = DatabaseManager(config.POSTGRES_DSN)
broker = MessageBroker(config.BUS_BROKER)

# Initialize services
job_service = JobService(db, broker)

# Initialize lifecycle handler
lifecycle_handler = LifecycleHandler(db, broker, job_service)

app = FastAPI(title="Main API Service", version="1.0.0")

# Include API routers
app.include_router(job_router)
app.include_router(health_router)
app.include_router(video_router)
app.include_router(image_router)
app.include_router(features_router)


@app.on_event("startup")
async def startup() -> None:
    """
    Initialize connections and services on application startup.
    This function is called by FastAPI when the application starts.
    """
    await lifecycle_handler.startup()


@app.on_event("shutdown")
async def shutdown() -> None:
    """
    Clean up connections and resources on application shutdown.
    This function is called by FastAPI when the application is shutting down.
    """
    await lifecycle_handler.shutdown()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)