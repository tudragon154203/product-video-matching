import os
import asyncio
import sys
sys.path.append('/app/libs')

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from contracts.validator import validator
from evidence import EvidenceGenerator

# Configure logging
logger = configure_logging("evidence-builder")

# Environment variables
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:dev@postgres:5432/postgres")
BUS_BROKER = os.getenv("BUS_BROKER", "amqp://guest:guest@rabbitmq:5672/")
DATA_ROOT = os.getenv("DATA_ROOT", "/app/data")

# Global instances
db = DatabaseManager(POSTGRES_DSN)
broker = MessageBroker(BUS_BROKER)
evidence_generator = EvidenceGenerator(DATA_ROOT)


async def handle_match_result(event_data):
    """Handle match result event and generate evidence"""
    try:
        # Validate event
        validator.validate_event("match_result", event_data)
        
        job_id = event_data["job_id"]
        product_id = event_data["product_id"]
        video_id = event_data["video_id"]
        best_pair = event_data["best_pair"]
        score = event_data["score"]
        ts = event_data["ts"]
        
        logger.info("Processing match result for evidence", 
                   job_id=job_id, 
                   product_id=product_id, 
                   video_id=video_id,
                   score=score)
        
        # Get image and frame paths
        image_info = await get_image_info(best_pair["img_id"])
        frame_info = await get_frame_info(best_pair["frame_id"])
        
        if not image_info or not frame_info:
            logger.error("Failed to get image or frame info", 
                        img_id=best_pair["img_id"],
                        frame_id=best_pair["frame_id"])
            return
        
        # Generate evidence image
        evidence_path = await evidence_generator.create_evidence(
            image_path=image_info["local_path"],
            frame_path=frame_info["local_path"],
            img_id=best_pair["img_id"],
            frame_id=best_pair["frame_id"],
            score=score,
            timestamp=ts,
            kp_img_path=image_info.get("kp_blob_path"),
            kp_frame_path=frame_info.get("kp_blob_path")
        )
        
        if evidence_path:
            # Update match record with evidence path
            await db.execute(
                "UPDATE matches SET evidence_path = $1 WHERE product_id = $2 AND video_id = $3 AND job_id = $4",
                evidence_path, product_id, video_id, job_id
            )
            
            # Emit enriched match result
            enriched_event = {
                **event_data,
                "evidence_path": evidence_path
            }
            
            await broker.publish_event(
                "match.result.enriched",
                enriched_event,
                correlation_id=job_id
            )
            
            logger.info("Generated evidence", 
                       job_id=job_id,
                       product_id=product_id,
                       video_id=video_id,
                       evidence_path=evidence_path)
        else:
            logger.error("Failed to generate evidence", 
                        job_id=job_id,
                        product_id=product_id,
                        video_id=video_id)
        
    except Exception as e:
        logger.error("Failed to process match result", error=str(e))
        raise


async def get_image_info(img_id: str):
    """Get product image information"""
    query = "SELECT local_path, kp_blob_path FROM product_images WHERE img_id = $1"
    return await db.fetch_one(query, img_id)


async def get_frame_info(frame_id: str):
    """Get video frame information"""
    query = "SELECT local_path, kp_blob_path FROM video_frames WHERE frame_id = $1"
    return await db.fetch_one(query, frame_id)


async def main():
    """Main service loop"""
    try:
        # Initialize connections
        await db.connect()
        await broker.connect()
        
        # Subscribe to events
        await broker.subscribe_to_topic(
            "match.result",
            handle_match_result
        )
        
        logger.info("Evidence builder service started")
        
        # Keep service running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down evidence builder service")
    except Exception as e:
        logger.error("Service error", error=str(e))
    finally:
        await db.disconnect()
        await broker.disconnect()


if __name__ == "__main__":
    asyncio.run(main())