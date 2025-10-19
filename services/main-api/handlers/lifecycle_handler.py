from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging
from services.job.job_service import JobService
from services.phase.phase_event_service import PhaseEventService
from handlers.database_handler import DatabaseHandler
from handlers.broker_handler import BrokerHandler

logger = configure_logging("main-api:lifecycle_handler")


class LifecycleHandler:
    def __init__(self, db: DatabaseManager, job_service: JobService, broker=None):
        self.db = db
        self.broker = broker
        self.job_service = job_service

        # Initialize phase event service if broker is available
        if self.broker:
            db_handler = DatabaseHandler(db)
            broker_handler = BrokerHandler(broker)
            self.phase_event_service = PhaseEventService(db_handler, broker_handler)
        else:
            self.phase_event_service = None

    async def startup(self):
        """Initialize connections on startup"""
        try:
            await self.db.connect()
        except Exception as e:
            logger.warning(
                f"Failed to connect to database: {e}. "
                "Continuing without database connection."
            )

        if self.broker:
            try:
                await self.broker.connect()

                # Subscribe to phase completion events
                await self.subscribe_to_phase_events()

            except Exception as e:
                logger.warning(
                    f"Failed to connect to message broker: {e}. "
                    "Continuing without message broker connection."
                )

        logger.info("Main API service started")

    async def shutdown(self):
        """Clean up connections on shutdown"""
        await self.db.disconnect()
        logger.info("Main API service stopped")

    async def subscribe_to_phase_events(self):
        """Subscribe to phase completion events"""
        if not self.broker or not self.phase_event_service:
            logger.warning("Cannot subscribe to events: broker or phase_event_service not available")
            return

        try:
            # Subscribe to product collection completion events
            await self.broker.subscribe_to_topic(
                "products.collections.completed",
                self.handle_products_collections_completed,
            )

            # Subscribe to video collection completion events
            await self.broker.subscribe_to_topic(
                "videos.collections.completed",
                self.handle_videos_collections_completed,
            )

            logger.info("Subscribed to phase completion events")
        except Exception as e:
            logger.error(f"Failed to subscribe to phase events: {e}")
            raise

    async def handle_products_collections_completed(self, event_data, correlation_id):
        """Handle products collections completed event"""
        try:
            logger.info(
                "Handling products collections completed",
                job_id=event_data.get("job_id"),
                correlation_id=correlation_id,
            )
            await self.phase_event_service.handle_phase_event(
                "products.collections.completed", event_data
            )
            logger.info(f"Processed products collections completed event for job {event_data.get('job_id')}")
        except Exception as e:
            logger.error(f"Failed to handle products collections completed event: {e}")

    async def handle_videos_collections_completed(self, event_data, correlation_id):
        """Handle videos collections completed event"""
        try:
            logger.info(
                "Handling videos collections completed",
                job_id=event_data.get("job_id"),
                correlation_id=correlation_id,
            )
            await self.phase_event_service.handle_phase_event(
                "videos.collections.completed", event_data
            )
            logger.info(f"Processed videos collections completed event for job {event_data.get('job_id')}")
        except Exception as e:
            logger.error(f"Failed to handle videos collections completed event: {e}")
