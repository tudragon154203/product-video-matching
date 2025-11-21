"""Health check endpoint for evidence-builder service."""

import asyncio
from pathlib import Path
from typing import Dict, Any

from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.logging_config import configure_logging

logger = configure_logging("evidence-builder:health")


class HealthChecker:
    """Health check for evidence-builder service."""

    def __init__(
        self,
        db: DatabaseManager,
        broker: MessageBroker,
        evidence_dir: Path,
    ):
        self.db = db
        self.broker = broker
        self.evidence_dir = evidence_dir

    async def check_health(self) -> Dict[str, Any]:
        """
        Check health of all service dependencies.

        Returns:
            Dict with health status and details
        """
        health_status = {
            "service": "evidence-builder",
            "status": "healthy",
            "checks": {},
        }

        # Check database connectivity
        try:
            await self.db.fetch_val("SELECT 1")
            health_status["checks"]["database"] = {
                "status": "healthy",
                "message": "Database connection OK",
            }
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}",
            }

        # Check broker connectivity
        try:
            if self.broker.connection and not self.broker.connection.is_closed:
                health_status["checks"]["broker"] = {
                    "status": "healthy",
                    "message": "Broker connection OK",
                }
            else:
                health_status["status"] = "unhealthy"
                health_status["checks"]["broker"] = {
                    "status": "unhealthy",
                    "message": "Broker connection closed",
                }
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["broker"] = {
                "status": "unhealthy",
                "message": f"Broker check failed: {str(e)}",
            }

        # Check evidence directory is writable
        try:
            test_file = self.evidence_dir / ".health_check"
            test_file.touch()
            test_file.unlink()
            health_status["checks"]["evidence_dir"] = {
                "status": "healthy",
                "message": f"Evidence directory writable: {self.evidence_dir}",
            }
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["evidence_dir"] = {
                "status": "unhealthy",
                "message": f"Evidence directory not writable: {str(e)}",
            }

        return health_status
