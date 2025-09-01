import asyncio
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.logging_config import configure_logging
from config_loader import config
from services.job.job_service import JobService

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
        
        # Subscribe to phase events
        await self.subscribe_to_phase_events()
        
        logger.info("Main API service started")

    async def shutdown(self):
        """Clean up connections on shutdown"""
        await self.db.disconnect()
        await self.broker.disconnect()
        logger.info("Main API service stopped")
        
    async def subscribe_to_phase_events(self):
        """Subscribe to job-based completion events only"""
        try:
            # Subscribe to collection completion events (to transition from collection -> feature_extraction)
            await self.broker.subscribe_to_topic(
                "products.collections.completed",
                lambda event_data: self.job_service.handle_phase_event("products.collections.completed", event_data),
                "main_api_products_collections_completed"
            )

            await self.broker.subscribe_to_topic(
                "videos.collections.completed",
                lambda event_data: self.job_service.handle_phase_event("videos.collections.completed", event_data),
                "main_api_videos_collections_completed"
            )

            # Subscribe to feature extraction + downstream completion events
            await self.broker.subscribe_to_topic(
                "image.embeddings.completed",
                lambda event_data: self.job_service.handle_phase_event("image.embeddings.completed", event_data),
                "main_api_image_embeddings_completed"
            )
            
            await self.broker.subscribe_to_topic(
                "video.embeddings.completed",
                lambda event_data: self.job_service.handle_phase_event("video.embeddings.completed", event_data),
                "main_api_video_embeddings_completed"
            )
            
            await self.broker.subscribe_to_topic(
                "image.keypoints.completed",
                lambda event_data: self.job_service.handle_phase_event("image.keypoints.completed", event_data),
                "main_api_image_keypoints_completed"
            )
            
            await self.broker.subscribe_to_topic(
                "video.keypoints.completed",
                lambda event_data: self.job_service.handle_phase_event("video.keypoints.completed", event_data),
                "main_api_video_keypoints_completed"
            )
            
            await self.broker.subscribe_to_topic(
                "matchings.process.completed",
                lambda event_data: self.job_service.handle_phase_event("matchings.process.completed", event_data),
                "main_api_matchings_process_completed"
            )
            
            await self.broker.subscribe_to_topic(
                "evidences.generation.completed",
                lambda event_data: self.job_service.handle_phase_event("evidences.generation.completed", event_data),
                "main_api_evidences_generation_completed"
            )
            
            logger.info("Subscribed to all phase completion events")
        except Exception as e:
            logger.error("Failed to subscribe to job-based completion events", error=str(e))
