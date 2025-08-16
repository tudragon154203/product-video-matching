"""Database operations for segmentation results.

This module handles database updates for segmentation results, including:
- Updating product image records with mask file paths
- Updating video frame records with mask file paths
- Error handling for database operations

It serves as a specialized component that focuses solely on database operations,
delegating file management to the FileManager and image processing to other modules.
"""
from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging
from file_manager import FileManager

logger = configure_logging("product-segmentor")

class DatabaseUpdater:
    """Handles database updates for segmentation results.
    
    This class focuses solely on database operations for storing segmentation results,
    updating product images and video frames with their corresponding mask file paths.
    File management and image processing are delegated to other modules.
    """
    def __init__(self, db: DatabaseManager):
        """Initialize database updater with database connection.
        
        Args:
            db: Database manager instance for database operations
        """
        self.db = db

    async def update_product_image_mask(self, image_id: str, mask_path: str) -> None:
        """Update product image record with mask file path.
        
        Updates the product_images table to store the path to the generated mask file.
        This allows downstream services to access the segmented product region.
        
        Args:
            image_id: Unique identifier for the product image
            mask_path: Filesystem path to the generated mask file
            
        Note:
            Errors are logged but not raised to allow processing to continue
            with other images even if one fails.
        """
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
        """Update video frame record with mask file path.
        
        Updates the video_frames table to store the path to the generated mask file.
        This allows downstream services to access the segmented product region
        in video frames for matching operations.
        
        Args:
            frame_id: Unique identifier for the video frame
            mask_path: Filesystem path to the generated mask file
            
        Note:
            Errors are logged but not raised to allow processing to continue
            with other frames even if one fails.
        """
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
    """Handles file operations for segmentation results.
    
    This class focuses solely on file management operations for storing mask files,
    delegating database operations to DatabaseUpdater and image processing to other modules.
    """
    def __init__(self, file_manager: FileManager):
        """Initialize file processor with file manager.
        
        Args:
            file_manager: FileManager instance for file operations
        """
        self.file_manager = file_manager

    async def save_mask(self, image_id: str, mask: bytes, image_type: str) -> str:
        """Save mask to filesystem based on image type.
        
        Routes the mask to the appropriate file storage location based on whether
        it's a product image or video frame mask.
        
        Args:
            image_id: Unique identifier for the image/frame
            mask: Generated mask data as bytes
            image_type: Type of image ("product" or "frame")
            
        Returns:
            Path where the mask file was saved
            
        Note:
            This method simply routes to the FileManager's save methods.
            Actual file handling is implemented in the FileManager class.
        """
        if image_type == "product":
            return await self.file_manager.save_product_mask(image_id, mask)
        else:  # frame
            return await self.file_manager.save_frame_mask(image_id, mask)