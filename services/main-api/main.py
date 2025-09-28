from contextlib import asynccontextmanager
from middleware.static_file_logging import StaticFileLoggingMiddleware
from middleware.cors import add_cors_middleware
from api.results_endpoints import router as results_router
from api.features_endpoints import router as features_router
from api.product_endpoints import router as product_router
from api.static_endpoints import router as static_router
from api.image_endpoints import router as image_router
from api.video_endpoints import router as video_router
from api.health_endpoints import router as health_router
from api.job_endpoints import router as job_router
from handlers.lifecycle_handler import LifecycleHandler
from services.job.job_service import JobService
from api.dependency import init_dependencies, get_db, get_broker
from config_loader import config
from fastapi import FastAPI

from common_py.logging_config import configure_logging

# Configure logging
logger = configure_logging("main-api:main")

# Load service-specific configuration

# Initialize dependencies for the entire application
init_dependencies()

# Import services

# Import handlers

# Import API endpoints

# Import middleware

# Get shared instances only for lifecycle handler
db = get_db()
broker = get_broker()

# Initialize services
job_service = JobService(db, broker)

# Initialize lifecycle handler
lifecycle_handler = LifecycleHandler(db, broker, job_service)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for managing the lifespan of the FastAPI application.
    Initializes connections and services on startup, and cleans up on shutdown.
    """
    await lifecycle_handler.startup()
    yield
    await lifecycle_handler.shutdown()

app = FastAPI(title="Main API Service", version="1.0.0", lifespan=lifespan)

# Configure middleware
add_cors_middleware(app)
app.add_middleware(StaticFileLoggingMiddleware)

# Include API routers
app.include_router(job_router)
app.include_router(health_router)
app.include_router(video_router)
app.include_router(image_router)
app.include_router(static_router)
app.include_router(product_router)
app.include_router(features_router)
app.include_router(results_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
