import os
import asyncio
import sys

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import ProductImageCRUD, VideoFrameCRUD
from contracts.validator import validator
from embedding import EmbeddingExtractor

# Configure logging
logger = configure_logging("vision-embedding")

# Environment variables
from config import config

POSTGRES_DSN = config.POSTGRES_DSN
BUS_BROKER = config.BUS_BROKER
EMBED_MODEL = config.EMBED_MODEL

# Global instances
db = DatabaseManager(POSTGRES_DSN)
broker = MessageBroker(BUS_BROKER)
image_crud = ProductImageCRUD(db)
frame_crud = VideoFrameCRUD(db)
extractor = EmbeddingExtractor(EMBED_MODEL)


async def handle_products_images_ready(event_data):
    """Handle product images ready event"""
    try:
        # Validate event
        validator.validate_event("products_images_ready", event_data)
        
        product_id = event_data["product_id"]
        image_id = event_data["image_id"]
        local_path = event_data["local_path"]
        
        logger.info("Processing product image", image_id=image_id)
        
        # Extract embeddings
        emb_rgb, emb_gray = await extractor.extract_embeddings(local_path)
        
        if emb_rgb is not None and emb_gray is not None:
            # Update database with embeddings
            await image_crud.update_embeddings(image_id, emb_rgb.tolist(), emb_gray.tolist())
            
            # Emit features ready event
            await broker.publish_event(
                "features.ready",
                {
                    "entity_type": "product_image",
                    "id": image_id,
                    "emb_rgb": emb_rgb.tolist(),
                    "emb_gray": emb_gray.tolist()
                }
            )
            
            logger.info("Processed product image embeddings", image_id=image_id)
        else:
            logger.error("Failed to extract embeddings", image_id=image_id)
        
    except Exception as e:
        logger.error("Failed to process product image", error=str(e))
        raise


async def handle_videos_keyframes_ready(event_data):
    """Handle video keyframes ready event"""
    try:
        # Validate event
        validator.validate_event("videos_keyframes_ready", event_data)
        
        video_id = event_data["video_id"]
        frames = event_data["frames"]
        
        logger.info("Processing video frames", video_id=video_id, frame_count=len(frames))
        
        # Process each frame
        for frame_data in frames:
            frame_id = frame_data["frame_id"]
            local_path = frame_data["local_path"]
            
            # Extract embeddings
            emb_rgb, emb_gray = await extractor.extract_embeddings(local_path)
            
            if emb_rgb is not None and emb_gray is not None:
                # Update database with embeddings
                await frame_crud.update_embeddings(frame_id, emb_rgb.tolist(), emb_gray.tolist())
                
                # Emit features ready event
                await broker.publish_event(
                    "features.ready",
                    {
                        "entity_type": "video_frame",
                        "id": frame_id,
                        "emb_rgb": emb_rgb.tolist(),
                        "emb_gray": emb_gray.tolist()
                    }
                )
                
                logger.info("Processed video frame embeddings", frame_id=frame_id)
            else:
                logger.error("Failed to extract embeddings", frame_id=frame_id)
        
    except Exception as e:
        logger.error("Failed to process video frames", error=str(e))
        raise


async def main():
    """Main service loop"""
    try:
        # Initialize connections
        await db.connect()
        await broker.connect()
        await extractor.initialize()
        
        # Subscribe to events
        await broker.subscribe_to_topic(
            "products.images.ready",
            handle_products_images_ready
        )
        
        await broker.subscribe_to_topic(
            "videos.keyframes.ready",
            handle_videos_keyframes_ready
        )
        
        logger.info("Vision embedding service started")
        
        # Keep service running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down vision embedding service")
    except Exception as e:
        logger.error("Service error", error=str(e))
    finally:
        await extractor.cleanup()
        await db.disconnect()
        await broker.disconnect()


if __name__ == "__main__":
    asyncio.run(main())