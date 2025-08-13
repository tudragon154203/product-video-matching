from fastapi import APIRouter, HTTPException
import httpx
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from config_loader import config
from common_py.logging_config import configure_logging

# Configure logger
logger = configure_logging("main-api")

# Create router for health endpoints (no prefix)
router = APIRouter()

# We'll set these when including the router in main.py
db_instance = None
broker_instance = None

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection (if available)
        db_status = "unavailable"
        try:
            await db_instance.fetch_one("SELECT 1")
            db_status = "healthy"
        except Exception as e:
            logger.warning("Database health check failed", error=str(e))
            db_status = "unhealthy"
        
        # Check message broker connection (if available)
        broker_status = "unavailable"
        try:
            if broker_instance.connection:
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