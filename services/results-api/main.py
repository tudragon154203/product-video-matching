"""
Main application file for the Results API service.
Clean FastAPI application initialization with proper architecture.
"""
import sys
import os
import logging
from contextlib import asynccontextmanager

# Add the app directory to the Python path for bind mount setup
sys.path.append("/app/app")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.config import get_settings
from core.exceptions import register_exception_handlers
from core.dependencies import startup_dependencies, shutdown_dependencies
from core.mcp_setup import setup_mcp_server, validate_mcp_configuration
from api import router as api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""
    # Startup
    try:
        logger.info("Starting Results API service...")
        await startup_dependencies()
        logger.info("Results API service started successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to start Results API service: {e}")
        raise
    finally:
        # Shutdown
        try:
            logger.info("Shutting down Results API service...")
            await shutdown_dependencies()
            logger.info("Results API service shut down successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    # Get application settings
    settings = get_settings()
    
    # Create FastAPI application
    app = FastAPI(
        title=settings.app.title,
        version=settings.app.version,
        description="API for product-video matching results",
        debug=settings.app.debug,
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register exception handlers
    register_exception_handlers(app)
    
    # Include API routes
    app.include_router(api_router)
    
    # Add root endpoint
    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint"""
        return {
            "service": settings.app.title,
            "version": settings.app.version,
            "status": "running"
        }
    
    # Setup MCP server if enabled
    try:
        validate_mcp_configuration(settings.mcp)
        setup_mcp_server(app, settings.mcp)
        logger.info("MCP server setup completed")
    except Exception as e:
        logger.warning(f"MCP server setup failed: {e}")
        if settings.app.debug:
            raise
    
    logger.info(f"FastAPI application created: {settings.app.title} v{settings.app.version}")
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    
    # Configure uvicorn logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelprefix)s %(message)s"
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelprefix)s %(client_addr)s - \"%(request_line)s\" %(status_code)s"
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        log_level=settings.app.log_level.lower(),
        reload=settings.app.debug,
        log_config=log_config
    )
