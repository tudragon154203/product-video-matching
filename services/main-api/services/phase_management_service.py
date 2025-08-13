import asyncio
import logging
from common_py.logging_config import configure_logging
from handlers.database_handler import DatabaseHandler
from handlers.broker_handler import BrokerHandler

logger = configure_logging("main-api")

class PhaseManagementService:
    def __init__(self, db_handler: DatabaseHandler, broker_handler: BrokerHandler):
        self.db_handler = db_handler
        self.broker_handler = broker_handler

    async def update_job_phases(self):
        """Update job phases based on progress"""
        try:
            # Get all jobs that are not completed or failed
            jobs = await self.db_handler.get_jobs_for_phase_update()
            
            for job in jobs:
                job_id = job["job_id"]
                current_phase = job["phase"]
                
                # Get counts for this job
                product_count, video_count, match_count = await self.db_handler.get_job_counts(job_id)
                
                # Count products and videos with features
                products_with_features, videos_with_features = await self.db_handler.get_features_counts(job_id)
                
                # Determine new phase based on progress
                new_phase = current_phase
                
                if current_phase == "collection":
                    # Move to feature_extraction if we have products OR videos
                    if product_count > 0 or video_count > 0:
                        new_phase = "feature_extraction"
                
                elif current_phase == "feature_extraction":
                    # Move to matching if any products or videos have features
                    if products_with_features > 0 or videos_with_features > 0:
                        new_phase = "matching"
                        
                        # Publish match request when transitioning to matching phase
                        try:
                            # Get industry from job record
                            industry = await self.db_handler.get_job_industry(job_id)
                            
                            await self.broker_handler.publish_match_request(
                                job_id,
                                industry,
                                job_id,
                                job_id
                            )
                        except Exception as e:
                            logger.error("Failed to publish match request", job_id=job_id, error=str(e))
                
                elif current_phase == "matching":
                    # Move to evidence if we have matches
                    if match_count > 0:
                        new_phase = "evidence"
                    # Or move to completed if no matches found after reasonable time OR if we have products/videos but no matches
                    elif product_count > 0 and video_count > 0:
                        # Check if job is older than 5 minutes
                        job_age = await self.db_handler.get_job_age(job_id)
                        if job_age and job_age > 60:  # 1 minutes
                            new_phase = "completed"
                    # Handle case where we don't have both products and videos
                    elif product_count == 0 or video_count == 0:
                        # If we don't have both products and videos, we can't match, so complete the job
                        new_phase = "completed"
                    # Handle case where we have products and videos but no features
                    elif (product_count > 0 and products_with_features == 0) or (video_count > 0 and videos_with_features == 0):
                        # If we have items but no features, we can't match, so complete the job
                        new_phase = "completed"
                
                elif current_phase == "evidence":
                    # Move to completed
                    new_phase = "completed"
                
                # Update phase if it changed
                if new_phase != current_phase:
                    await self.db_handler.update_job_phase(job_id, new_phase)
                    logger.info("Updated job phase", job_id=job_id, 
                               old_phase=current_phase, new_phase=new_phase,
                               products=product_count, videos=video_count, 
                               products_with_features=products_with_features,
                               videos_with_features=videos_with_features,
                               matches=match_count)
                    
        except Exception as e:
            logger.error("Failed to update job phases", error=str(e))

    async def phase_update_task(self):
        """Background task to continuously update job phases"""
        while True:
            try:
                await self.update_job_phases()
                await asyncio.sleep(5)  # Update every 5 seconds
            except Exception as e:
                logger.error("Phase update task error", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error