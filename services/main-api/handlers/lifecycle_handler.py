from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging
from services.job_service import JobService

logger = configure_logging("main-api:lifecycle_handler")


class LifecycleHandler:
    def __init__(self, db: DatabaseManager, job_service: JobService):
        self.db = db
        # Removed broker since it's no longer used
        self.job_service = job_service

    async def startup(self):
        """Initialize connections on startup"""
        try:
            await self.db.connect()
        except Exception as e:
            logger.warning(
                f"Failed to connect to database: {e}. "
                "Continuing without database connection."
            )

        logger.info("Main API service started")

    async def shutdown(self):
        """Clean up connections on shutdown"""
        await self.db.disconnect()
        logger.info("Main API service stopped")

    # Removed subscribe_to_phase_events method since it depends on broker which is no longer used
