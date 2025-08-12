import os
import asyncio
import uuid
import sys
sys.path.append('/app/libs')

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import MatchCRUD
from common_py.models import Match
from contracts.validator import validator
from matching import MatchingEngine

# Configure logging
logger = configure_logging("matcher")

# Environment variables
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:dev@postgres:5432/postgres")
BUS_BROKER = os.getenv("BUS_BROKER", "amqp://guest:guest@rabbitmq:5672/")
DATA_ROOT = os.getenv("DATA_ROOT", "/app/data")
VECTOR_INDEX_URL = os.getenv("VECTOR_INDEX_URL", "http://vector-index:8081")

# Matching parameters
RETRIEVAL_TOPK = int(os.getenv("RETRIEVAL_TOPK", "20"))
SIM_DEEP_MIN = float(os.getenv("SIM_DEEP_MIN", "0.82"))
INLIERS_MIN = float(os.getenv("INLIERS_MIN", "0.35"))
MATCH_BEST_MIN = float(os.getenv("MATCH_BEST_MIN", "0.88"))
MATCH_CONS_MIN = int(os.getenv("MATCH_CONS_MIN", "2"))
MATCH_ACCEPT = float(os.getenv("MATCH_ACCEPT", "0.80"))

# Global instances
db = DatabaseManager(POSTGRES_DSN)
broker = MessageBroker(BUS_BROKER)
match_crud = MatchCRUD(db)
matching_engine = MatchingEngine(
    db, DATA_ROOT, VECTOR_INDEX_URL,
    retrieval_topk=RETRIEVAL_TOPK,
    sim_deep_min=SIM_DEEP_MIN,
    inliers_min=INLIERS_MIN,
    match_best_min=MATCH_BEST_MIN,
    match_cons_min=MATCH_CONS_MIN,
    match_accept=MATCH_ACCEPT
)


async def handle_match_request(event_data):
    """Handle match request event"""
    try:
        # Validate event
        validator.validate_event("match_request", event_data)
        
        job_id = event_data["job_id"]
        industry = event_data["industry"]
        product_set_id = event_data["product_set_id"]
        video_set_id = event_data["video_set_id"]
        top_k = event_data["top_k"]
        
        logger.info("Processing match request", 
                   job_id=job_id, industry=industry)
        
        # Get products and videos for this job
        products = await get_job_products(job_id)
        videos = await get_job_videos(job_id)
        
        logger.info("Found entities for matching", 
                   job_id=job_id, 
                   product_count=len(products),
                   video_count=len(videos))
        
        # Perform matching for each product-video pair
        total_matches = 0
        for product in products:
            for video in videos:
                match_result = await matching_engine.match_product_video(
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
                    
                    await match_crud.create_match(match)
                    
                    # Emit match result event
                    await broker.publish_event(
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
        
        logger.info("Completed matching", 
                   job_id=job_id, 
                   total_matches=total_matches)
        
    except Exception as e:
        logger.error("Failed to process match request", error=str(e))
        raise


async def get_job_products(job_id: str):
    """Get all products for a job"""
    query = """
    SELECT DISTINCT p.product_id, p.title
    FROM products p
    WHERE p.job_id = $1
    """
    return await db.fetch_all(query, job_id)


async def get_job_videos(job_id: str):
    """Get all videos for a job"""
    query = """
    SELECT DISTINCT v.video_id, v.title
    FROM videos v
    WHERE v.job_id = $1
    """
    return await db.fetch_all(query, job_id)


async def main():
    """Main service loop"""
    try:
        # Initialize connections
        await db.connect()
        await broker.connect()
        await matching_engine.initialize()
        
        # Subscribe to events
        await broker.subscribe_to_topic(
            "match.request",
            handle_match_request
        )
        
        logger.info("Matcher service started")
        
        # Keep service running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down matcher service")
    except Exception as e:
        logger.error("Service error", error=str(e))
    finally:
        await matching_engine.cleanup()
        await db.disconnect()
        await broker.disconnect()


if __name__ == "__main__":
    asyncio.run(main())