import asyncio
from typing import Dict, Any
import structlog
from prefect import flow, task

logger = structlog.get_logger()


class MatchingFlow:
    """Prefect flow for orchestrating the matching pipeline"""
    
    def __init__(self, job_id: str, request, db, broker):
        self.job_id = job_id
        self.request = request
        self.db = db
        self.broker = broker
    
    async def run(self):
        """Run the complete matching flow"""
        try:
            logger.info("Starting matching flow", job_id=self.job_id)
            
            # Phase 1: Collection
            await self.update_job_phase("collection")
            await self.emit_collection_events()
            
            # Wait for collection to complete (simplified for MVP)
            await asyncio.sleep(5)
            
            # Phase 2: Feature extraction
            await self.update_job_phase("feature_extraction")
            # Features are extracted automatically when images/frames are ready
            
            # Wait for feature extraction (simplified for MVP)
            await asyncio.sleep(10)
            
            # Phase 3: Matching
            await self.update_job_phase("matching")
            await self.emit_match_request()
            
            # Wait for matching to complete
            await asyncio.sleep(5)
            
            # Phase 4: Evidence generation
            await self.update_job_phase("evidence")
            # Evidence is generated automatically when matches are found
            
            # Wait for evidence generation
            await asyncio.sleep(3)
            
            # Phase 5: Complete
            await self.update_job_phase("completed")
            
            logger.info("Matching flow completed", job_id=self.job_id)
            
        except Exception as e:
            logger.error("Matching flow failed", job_id=self.job_id, error=str(e))
            await self.update_job_phase("failed")
    
    async def update_job_phase(self, phase: str):
        """Update job phase in database"""
        await self.db.execute(
            "UPDATE jobs SET phase = $1, updated_at = CURRENT_TIMESTAMP WHERE job_id = $2",
            phase, self.job_id
        )
        logger.info("Updated job phase", job_id=self.job_id, phase=phase)
    
    async def emit_collection_events(self):
        """Emit events to start product and video collection"""
        
        # Emit product collection request
        product_event = {
            "job_id": self.job_id,
            "top_amz": self.request.top_amz,
            "top_ebay": self.request.top_ebay,
            "queries": {
                "en": self.request.product_queries  # Assume request has product_queries field
            }
        }
        
        await self.broker.publish_event(
            "products.collect.request",
            product_event,
            correlation_id=self.job_id
        )
        
        # Emit video search request
        video_event = {
            "job_id": self.job_id,
            "industry": self.request.industry,
            "queries": {
                "vi": self.request.video_queries_vi,
                "zh": self.request.video_queries_zh
            },
            "platforms": self.request.platforms,
            "recency_days": self.request.recency_days
        }
        
        await self.broker.publish_event(
            "videos.search.request",
            video_event,
            correlation_id=self.job_id
        )
        
        logger.info("Emitted collection events", job_id=self.job_id)
    
    async def emit_match_request(self):
        """Emit match request event"""
        match_event = {
            "job_id": self.job_id,
            "industry": self.request.industry,
            "product_set_id": self.job_id,  # Use job_id as set identifier
            "video_set_id": self.job_id,
            "top_k": 20  # Default retrieval count
        }
        
        await self.broker.publish_event(
            "match.request",
            match_event,
            correlation_id=self.job_id
        )
        
        logger.info("Emitted match request", job_id=self.job_id)