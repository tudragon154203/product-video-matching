import uuid
from typing import Dict, Any, List
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import MatchCRUD
from common_py.models import Match
from common_py.logging_config import configure_logging
from matching import MatchingEngine

logger = configure_logging("matcher")


class MatcherService:
    """Main service class for matching"""
    
    def __init__(self, db: DatabaseManager, broker: MessageBroker, data_root: str, **params):
        self.db = db
        self.broker = broker
        self.match_crud = MatchCRUD(db)
        self.matching_engine = MatchingEngine(db, data_root, **params)
    
    async def initialize(self):
        """Initialize the matching engine"""
        await self.matching_engine.initialize()
    
    async def cleanup(self):
        """Clean up resources"""
        await self.matching_engine.cleanup()
    
    async def handle_match_request(self, event_data: Dict[str, Any]):
        """Handle match request event"""
        try:
            job_id = event_data["job_id"]
            industry = event_data["industry"]
            product_set_id = event_data["product_set_id"]
            video_set_id = event_data["video_set_id"]
            top_k = event_data["top_k"]
            
            logger.info("Processing match request", 
                       job_id=job_id, industry=industry)
            
            # Get products and videos for this job
            products = await self.get_job_products(job_id)
            videos = await self.get_job_videos(job_id)
            
            logger.info("Found entities for matching", 
                       job_id=job_id, 
                       product_count=len(products),
                       video_count=len(videos))
            
            # Perform matching for each product-video pair
            total_matches = 0
            for product in products:
                for video in videos:
                    match_result = await self.matching_engine.match_product_video(
                        product["product_id"], 
                        video["video_id"],
                        job_id
                    )
                    
                    if match_result:
                        # Create match record
                        match = Match(
                            match_id=str(uuid.uuid4()),
                            job_id=job_id,
                            product_id=product["product_id"],
                            video_id=video["video_id"],
                            best_img_id=match_result["best_img_id"],
                            best_frame_id=match_result["best_frame_id"],
                            ts=match_result["ts"],
                            score=match_result["score"]
                        )
                        
                        await self.match_crud.create_match(match)
                        
                        # Emit match result event
                        await self.broker.publish_event(
                            "match.result",
                            {
                                "job_id": job_id,
                                "product_id": product["product_id"],
                                "video_id": video["video_id"],
                                "best_pair": {
                                    "img_id": match_result["best_img_id"],
                                    "frame_id": match_result["best_frame_id"],
                                    "score_pair": match_result["best_pair_score"]
                                },
                                "score": match_result["score"],
                                "ts": match_result["ts"]
                            },
                            correlation_id=job_id
                        )
                        
                        total_matches += 1
                        
                        logger.info("Found match", 
                                   job_id=job_id,
                                   product_id=product["product_id"],
                                   video_id=video["video_id"],
                                   score=match_result["score"])
            
            # Emit matchings process completed event
            event_id = str(uuid.uuid4())
            await self.broker.publish_event(
                "matchings.process.completed",
                {
                    "job_id": job_id,
                    "event_id": event_id
                },
                correlation_id=job_id
            )
            
            logger.info("Completed matching", 
                       job_id=job_id, 
                       total_matches=total_matches)
            
        except Exception as e:
            logger.error("Failed to process match request", error=str(e))
            raise
    
    async def get_job_products(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all products for a job"""
        query = """
        SELECT DISTINCT p.product_id, p.title
        FROM products p
        WHERE p.job_id = $1
        """
        return await self.db.fetch_all(query, job_id)
    
    async def get_job_videos(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all videos for a job"""
        query = """
        SELECT DISTINCT v.video_id, v.title
        FROM videos v
        WHERE v.job_id = $1
        """
        return await self.db.fetch_all(query, job_id)