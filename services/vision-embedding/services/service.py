import structlog
from typing import Dict, Any, List
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import ProductImageCRUD, VideoFrameCRUD
from embedding import EmbeddingExtractor

logger = structlog.get_logger()


class VisionEmbeddingService:
    """Main service class for vision embedding"""
    
    def __init__(self, db: DatabaseManager, broker: MessageBroker, embed_model: str):
        self.db = db
        self.broker = broker
        self.image_crud = ProductImageCRUD(db)
        self.frame_crud = VideoFrameCRUD(db)
        self.extractor = EmbeddingExtractor(embed_model)
    
    async def initialize(self):
        """Initialize the embedding extractor"""
        await self.extractor.initialize()
    
    async def cleanup(self):
        """Clean up resources"""
        await self.extractor.cleanup()
    
    async def handle_products_images_ready(self, event_data: Dict[str, Any]):
        """Handle product images ready event"""
        try:
            product_id = event_data["product_id"]
            image_id = event_data["image_id"]
            local_path = event_data["local_path"]
            
            logger.info("Processing product image", image_id=image_id)
            
            # Extract embeddings
            emb_rgb, emb_gray = await self.extractor.extract_embeddings(local_path)
            
            if emb_rgb is not None and emb_gray is not None:
                # Update database with embeddings
                await self.image_crud.update_embeddings(image_id, emb_rgb.tolist(), emb_gray.tolist())
                
                # Emit features ready event
                await self.broker.publish_event(
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
    
    async def handle_videos_keyframes_ready(self, event_data: Dict[str, Any]):
        """Handle video keyframes ready event"""
        try:
            video_id = event_data["video_id"]
            frames = event_data["frames"]
            
            logger.info("Processing video frames", video_id=video_id, frame_count=len(frames))
            
            # Process each frame
            for frame_data in frames:
                frame_id = frame_data["frame_id"]
                local_path = frame_data["local_path"]
                
                # Extract embeddings
                emb_rgb, emb_gray = await self.extractor.extract_embeddings(local_path)
                
                if emb_rgb is not None and emb_gray is not None:
                    # Update database with embeddings
                    await self.frame_crud.update_embeddings(frame_id, emb_rgb.tolist(), emb_gray.tolist())
                    
                    # Emit features ready event
                    await self.broker.publish_event(
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