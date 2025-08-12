import os
import asyncio
import sys
sys.path.append('/app/libs')

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from contracts.validator import validator
from keypoint import KeypointExtractor

# Configure logging
logger = configure_logging("vision-keypoint")

# Environment variables
sys.path.append('/app/infra')
from config import config

POSTGRES_DSN = config.POSTGRES_DSN
BUS_BROKER = config.BUS_BROKER
DATA_ROOT = config.DATA_ROOT

# Global instances
db = DatabaseManager(POSTGRES_DSN)
broker = MessageBroker(BUS_BROKER)
extractor = KeypointExtractor(DATA_ROOT)


async def handle_products_images_ready(event_data):
    """Handle product images ready event"""
    try:
        # Validate event
        validator.validate_event("products_images_ready", event_data)
        
        product_id = event_data["product_id"]
        image_id = event_data["image_id"]
        local_path = event_data["local_path"]
        
        logger.info("Processing product image keypoints", image_id=image_id)
        
        # Extract keypoints
        kp_blob_path = await extractor.extract_keypoints(local_path, image_id)
        
        if kp_blob_path:
            # Update database with keypoint path
            await db.execute(
                "UPDATE product_images SET kp_blob_path = $1 WHERE img_id = $2",
                kp_blob_path, image_id
            )
            
            # Emit features ready event with keypoint path
            await broker.publish_event(
                "features.ready",
                {
                    "entity_type": "product_image",
                    "id": image_id,
                    "emb_rgb": [],  # Will be filled by embedding service
                    "emb_gray": [],
                    "kp_blob_path": kp_blob_path
                }
            )
            
            logger.info("Processed product image keypoints", 
                       image_id=image_id, kp_path=kp_blob_path)
        else:
            logger.error("Failed to extract keypoints", image_id=image_id)
        
    except Exception as e:
        logger.error("Failed to process product image keypoints", error=str(e))
        raise


async def handle_videos_keyframes_ready(event_data):
    """Handle video keyframes ready event"""
    try:
        # Validate event
        validator.validate_event("videos_keyframes_ready", event_data)
        
        video_id = event_data["video_id"]
        frames = event_data["frames"]
        
        logger.info("Processing video frame keypoints", 
                   video_id=video_id, frame_count=len(frames))
        
        # Process each frame
        for frame_data in frames:
            frame_id = frame_data["frame_id"]
            local_path = frame_data["local_path"]
            
            # Extract keypoints
            kp_blob_path = await extractor.extract_keypoints(local_path, frame_id)
            
            if kp_blob_path:
                # Update database with keypoint path
                await db.execute(
                    "UPDATE video_frames SET kp_blob_path = $1 WHERE frame_id = $2",
                    kp_blob_path, frame_id
                )
                
                # Emit features ready event with keypoint path
                await broker.publish_event(
                    "features.ready",
                    {
                        "entity_type": "video_frame",
                        "id": frame_id,
                        "emb_rgb": [],  # Will be filled by embedding service
                        "emb_gray": [],
                        "kp_blob_path": kp_blob_path
                    }
                )
                
                logger.info("Processed video frame keypoints", 
                           frame_id=frame_id, kp_path=kp_blob_path)
            else:
                logger.error("Failed to extract keypoints", frame_id=frame_id)
        
    except Exception as e:
        logger.error("Failed to process video frame keypoints", error=str(e))
        raise


async def main():
    """Main service loop"""
    try:
        # Initialize connections
        await db.connect()
        await broker.connect()
        
        # Subscribe to events
        await broker.subscribe_to_topic(
            "products.images.ready",
            handle_products_images_ready
        )
        
        await broker.subscribe_to_topic(
            "videos.keyframes.ready",
            handle_videos_keyframes_ready
        )
        
        logger.info("Vision keypoint service started")
        
        # Keep service running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down vision keypoint service")
    except Exception as e:
        logger.error("Service error", error=str(e))
    finally:
        await db.disconnect()
        await broker.disconnect()


if __name__ == "__main__":
    asyncio.run(main())