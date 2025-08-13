import asyncio
import logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.logging_config import configure_logging
from config_loader import config
from services.job_service import JobService

logger = configure_logging("main-api")

class LifecycleHandler:
    def __init__(self, db: DatabaseManager, broker: MessageBroker, job_service: JobService):
        self.db = db
        self.broker = broker
        self.job_service = job_service

    async def startup(self):
        """Initialize connections on startup"""
        postgres_dsn = config.POSTGRES_DSN
        logger.info(f"Connecting to database with DSN: {postgres_dsn}")
        try:
            await self.db.connect()
        except Exception as e:
            logger.warning(f"Failed to connect to database: {e}. Continuing without database connection.")
        
        broker_url = config.BUS_BROKER
        logger.info(f"Connecting to message broker: {broker_url}")
        try:
            await self.broker.connect()
        except Exception as e:
            logger.warning(f"Failed to connect to message broker: {e}. Continuing without broker connection.")
        
        # Start background task for phase updates
        asyncio.create_task(self.job_service.phase_update_task())
        
        logger.info("Main API service started")

    async def shutdown(self):
        """Clean up connections on shutdown"""
        await self.db.disconnect()
        await self.broker.disconnect()
        logger.info("Main API service stopped")