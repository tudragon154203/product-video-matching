import structlog
from typing import Dict, Any, List
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from keypoint import KeypointExtractor

logger = structlog.get_logger()


class VisionKeypointService:
    """Main service class for vision keypoint extraction"""
    
    def __init__(self, db: DatabaseManager, broker: MessageBroker, data_root: str):
        self.db = db
        self.broker = broker
        self.extractor = KeypointExtractor(data_root)
    
    async def handle_products_images_ready(self, event_data: Dict[str, Any]):
        """Handle product images ready event"""
        try:
            product_id = event_data["product_id"]
            image_id = event_data["image_id"]
            local_path = event_data["local_path"]
            
            logger.info("Processing product image keypoints", image_id=image_id)
            
            # Extract keypoints
            kp_blob_path = await self.extractor.extract_keypoints(local_path, image_id)
            
            if kp_blob_path:
                # Update database with keypoint path
                await self.db.execute(
                    "UPDATE product_images SET kp_blob_path = $1 WHERE img_id = $2",
                    kp_blob_path, image_id
                )
                
                # Emit features ready event with keypoint path
                await self.broker.publish_event(
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
    
    async def handle_videos_keyframes_ready(self, event_data: Dict[str, Any]):
        """Handle video keyframes ready event"""
        try:
            video_id = event_data["video_id"]
            frames = event_data["frames"]
            
            logger.info("Processing video frame keypoints", 
                       video_id=video_id, frame_count=len(frames))
            
            # Process each frame
            for frame_data in frames:
                frame_id = frame_data["frame_id"]
                local_path = frame_data["local_path"]
                
                # Extract keypoints
                kp_blob_path = await self.extractor.extract_keypoints(local_path, frame_id)
                
                if kp_blob_path:
                    # Update database with keypoint path
                    await self.db.execute(
                        "UPDATE video_frames SET kp_blob_path = $1 WHERE frame_id = $2",
                        kp_blob_path, frame_id
                    )
                    
                    # Emit features ready event with keypoint path
                    await self.broker.publish_event(
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