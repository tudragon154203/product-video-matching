import structlog
from typing import Dict, Any, Optional
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from evidence import EvidenceGenerator

logger = structlog.get_logger()


class EvidenceBuilderService:
    """Main service class for evidence building"""
    
    def __init__(self, db: DatabaseManager, broker: MessageBroker, data_root: str):
        self.db = db
        self.broker = broker
        self.evidence_generator = EvidenceGenerator(data_root)
    
    async def handle_match_result(self, event_data: Dict[str, Any]):
        """Handle match result event and generate evidence"""
        try:
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
            image_info = await self.get_image_info(best_pair["img_id"])
            frame_info = await self.get_frame_info(best_pair["frame_id"])
            
            if not image_info or not frame_info:
                logger.error("Failed to get image or frame info", 
                            img_id=best_pair["img_id"],
                            frame_id=best_pair["frame_id"])
                return
            
            # Generate evidence image
            evidence_path = await self.evidence_generator.create_evidence(
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
                await self.db.execute(
                    "UPDATE matches SET evidence_path = $1 WHERE product_id = $2 AND video_id = $3 AND job_id = $4",
                    evidence_path, product_id, video_id, job_id
                )
                
                # Emit enriched match result
                enriched_event = {
                    **event_data,
                    "evidence_path": evidence_path
                }
                
                await self.broker.publish_event(
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
    
    async def get_image_info(self, img_id: str):
        """Get product image information"""
        query = "SELECT local_path, kp_blob_path FROM product_images WHERE img_id = $1"
        return await self.db.fetch_one(query, img_id)
    
    async def get_frame_info(self, frame_id: str):
        """Get video frame information"""
        query = "SELECT local_path, kp_blob_path FROM video_frames WHERE frame_id = $1"
        return await self.db.fetch_one(query, frame_id)