"""Database operations and file management for segmentation results."""
from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging
from file_manager import FileManager

logger = configure_logging("product-segmentor")

class DatabaseUpdater:
    def __init__(self, db: DatabaseManager):
        self.db = db

    async def update_product_image_mask(self, image_id: str, mask_path: str) -> None:
        """Update product image record with mask path."""
        try:
            query = """
                UPDATE product_images 
                SET masked_local_path = $1 
                WHERE img_id = $2
            """
            await self.db.execute(query, mask_path, image_id)
            
        except Exception as e:
            logger.error("Failed to update product image mask", image_id=image_id, error=str(e))

    async def update_video_frame_mask(self, frame_id: str, mask_path: str) -> None:
        """Update video frame record with mask path."""
        try:
            query = """
                UPDATE video_frames 
                SET masked_local_path = $1 
                WHERE frame_id = $2
            """
            await self.db.execute(query, mask_path, frame_id)
            
        except Exception as e:
            logger.error("Failed to update video frame mask", frame_id=frame_id, error=str(e))

class FileProcessor:
    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager

    async def save_mask(self, image_id: str, mask: bytes, image_type: str) -> str:
        """Save mask to filesystem based on image type."""
        if image_type == "product":
            return await self.file_manager.save_product_mask(image_id, mask)
        else:  # frame
            return await self.file_manager.save_frame_mask(image_id, mask)