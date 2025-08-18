"""
Health check utilities for services
"""
import asyncio
from typing import Dict, Any
from .logging_config import configure_logging

logger = configure_logging("common-py")


class HealthChecker:
    """Health check utilities for services"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.checks = {}
    
    def add_check(self, name: str, check_func):
        """Add a health check function"""
        self.checks[name] = check_func
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        status = {
            "service": self.service_name,
            "status": "healthy",
            "checks": {},
            "timestamp": asyncio.get_event_loop().time()
        }
        
        overall_healthy = True
        
        for check_name, check_func in self.checks.items():
            try:
                check_result = await check_func()
                status["checks"][check_name] = {
                    "status": "healthy" if check_result else "unhealthy",
                    "details": check_result if isinstance(check_result, dict) else {}
                }
                
                if not check_result:
                    overall_healthy = False
                    
            except Exception as e:
                status["checks"][check_name] = {
                    "status": "error",
                    "error": str(e)
                }
                overall_healthy = False
        
        status["status"] = "healthy" if overall_healthy else "unhealthy"
        return status


# Common health check functions
async def check_database_connection(db):
    """Check database connection"""
    try:
        await db.fetch_val("SELECT 1")
        return True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False


async def check_message_broker_connection(broker):
    """Check message broker connection"""
    try:
        # Simple check - if broker object exists and has connection
        return broker.connection is not None and not broker.connection.is_closed
    except Exception as e:
        logger.error("Message broker health check failed", error=str(e))
        return False