"Integration tests for Product Segmentor Service."

import pytest
import asyncio
import numpy as np
from unittest.mock import AsyncMock, Mock, patch
import tempfile
import shutil
import uuid
import os
from PIL import Image
import cv2

from services.service import ProductSegmentorService
from segmentation.interface import SegmentationInterface
from config_loader import config


class MockSegmentor(SegmentationInterface):
    """Mock segmentor for testing."""
    
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self._initialized = False
        self.call_count = 0
    
    async def initialize(self) -> None:
        if self.should_fail:
            raise Exception("Mock initialization failed")
        self._initialized = True
    
    async def segment_image(self, image_path: str) -> np.ndarray:
        self.call_count += 1
        if self.should_fail:
            return None
        return np.ones((100, 100, 1), dtype=np.uint8) * 255
    
    def cleanup(self) -> None:
        self._initialized = False
    
    @property
    def model_name(self) -> str:
        return "mock"
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized


class TestProductSegmentorServiceIntegration:
    """Integration tests for the complete service."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_db(self):
        """Mock database manager."""
        db = AsyncMock()
        db.execute = AsyncMock()
        return db
    
    @pytest.fixture
    def mock_broker(self):
        """Mock message broker."""
        broker = AsyncMock()
        broker.publish_event = AsyncMock()
        return broker
    
    @pytest.fixture
    def service(self, mock_db, mock_broker, temp_dir):
        """Create service with mocked dependencies."""
        # Create mock segmentor first
        mock_segmentor = MockSegmentor()
        mock_segmentor._initialized = True  # Pre-initialize the mock
        
        # Create mock for YOLOSegmentor
        mock_yolo_segmentor = MockSegmentor()
        mock_yolo_segmentor._initialized = True
        
        with patch('services.service.create_segmentor', return_value=mock_segmentor):
            with patch('services.service.YOLOSegmentor', return_value=mock_yolo_segmentor):
                service = ProductSegmentorService(
                    db=mock_db,
                    broker=mock_broker,
                    foreground_model_name="test/model", # Mock model name
                    max_concurrent=2
                )
                
                # Mock the event emitter to track calls without affecting the actual broker
                service.event_emitter.emit_product_image_masked = AsyncMock()
                service.event_emitter.emit_products_images_masked_batch = AsyncMock()
                service.event_emitter.emit_video_keyframes_masked = AsyncMock()
                service.event_emitter.emit_videos_keyframes_masked_batch = AsyncMock()
                service.event_emitter.emit_products_images_masked_completed = AsyncMock()
                service.event_emitter.emit_video_keyframes_masked_completed = AsyncMock()
                
                return service
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """Test service initialization."""
        await service.initialize()
        
        assert service.initialized
        assert service.foreground_segmentor.is_initialized
    
    @pytest.mark.asyncio
    async def test_service_initialization_failure(self, service):
        """Test service initialization failure."""
        service.foreground_segmentor = MockSegmentor(should_fail=True)
        
        with pytest.raises(Exception):
            await service.initialize()
        
        assert not service.initialized
    
    @pytest.mark.asyncio
    async def test_handle_products_image_ready(self, service, temp_dir):
        """Test handling product images ready event."""
        await service.initialize()
        
        # Create test image
        source_image_path = os.path.join(os.path.dirname(__file__), 'test_image.webp')
        test_image_path = os.path.join(temp_dir, f"test_image_{uuid.uuid4()}.webp")
        shutil.copy(source_image_path, test_image_path)
        
        event_data = {
            "product_id": "prod_123",
            "image_id": "img_123",
            "local_path": test_image_path,
            "job_id": "job_123"
        }
        
        # Mock save_product_mask to return a valid path and create a dummy file
        mock_mask_path = os.path.join(temp_dir, f"product_mask_img_123.png")
        with patch.object(service.file_manager, 'save_product_mask', return_value=mock_mask_path) as mock_save, \
             patch('cv2.imread', return_value=np.ones((100, 100), dtype=np.uint8) * 255):
            # Create a dummy mask file for cv2.imread to find
            Image.fromarray(np.ones((100, 100), dtype=np.uint8) * 255, mode='L').save(mock_mask_path)
            await service.handle_products_image_ready(event_data)
        
        # Verify segmentation was called
        assert service.foreground_segmentor.call_count == 1
        
        # Verify mask was saved
        mock_save.assert_called_once()
        
        # Verify database was updated
        service.db.execute.assert_called_once()
        
        # Verify event was published via event_emitter
        # Calculate the expected final mask path based on FileManager's logic
        from config_loader import config
        from pathlib import Path
        expected_mask_path_obj = Path(config.PRODUCT_MASK_DIR_PATH) / "products" / f"{event_data['image_id']}.png"
        expected_mask_path = str(expected_mask_path_obj)

        service.event_emitter.emit_product_image_masked.assert_called_once_with(
            job_id="job_123",
            image_id="img_123",
            mask_path=expected_mask_path
        )
    
    @pytest.mark.asyncio
    async def test_product_mask_subtraction(self, service, temp_dir):
        """Test that people mask is correctly subtracted from foreground mask."""
        await service.initialize()

        # Define mock masks
        image_size = (100, 100)
        foreground_mask = np.ones(image_size, dtype=np.uint8) * 255  # All white
        people_mask = np.zeros(image_size, dtype=np.uint8)  # All black
        # Draw a black square in the middle of the people mask
        people_mask[25:75, 25:75] = 255

        # Expected final mask: foreground_mask with the people_mask area blacked out
        expected_final_mask = cv2.bitwise_and(foreground_mask, cv2.bitwise_not(people_mask))

        # Mock segmentors to return our predefined masks
        service.foreground_segmentor.segment_image = AsyncMock(return_value=foreground_mask)
        service.people_segmentor.segment_image = AsyncMock(return_value=people_mask)

        # Mock save_product_final_mask to capture the mask it receives
        captured_final_mask = None
        async def mock_save_product_final_mask(image_id, mask, image_type):
            nonlocal captured_final_mask
            captured_final_mask = mask
            return os.path.join(temp_dir, f"final_mask_{image_id}.png") # Return a dummy path

        with patch.object(service.file_manager, 'save_product_final_mask', side_effect=mock_save_product_final_mask):
            event_data = {
                "product_id": "prod_subtraction_test",
                "image_id": "img_subtraction_test",
                "local_path": os.path.join(os.path.dirname(__file__), 'test_image.webp'),
                "job_id": "job_subtraction_test"
            }
            await service.handle_products_image_ready(event_data)

        # Assert that the captured final mask matches the expected result
        assert captured_final_mask is not None
        np.testing.assert_array_equal(captured_final_mask, expected_final_mask)

        # Verify segmentors were called
        service.foreground_segmentor.segment_image.assert_called_once()
        service.people_segmentor.segment_image.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_products_images_ready_batch_empty(self, service):
        """Test handling empty product images batch."""
        await service.initialize()
        
        event_data = {
            "job_id": "job_123",
            "total_images": 0
        }
        
        await service.handle_products_images_ready_batch(event_data)
        
        # Verify immediate batch completion event was published via event_emitter
        service.event_emitter.emit_products_images_masked_batch.assert_called_once_with(
            job_id="job_123",
            total_images=0
        )
    
    @pytest.mark.asyncio
    async def test_handle_videos_keyframes_ready(self, service, temp_dir):
        """Test handling video keyframes ready event."""
        await service.initialize()
        
        # Create test images for frames
        source_image_path = os.path.join(os.path.dirname(__file__), 'test_image.webp')
        frame1_path = os.path.join(temp_dir, f"frame1_{uuid.uuid4()}.webp")
        frame2_path = os.path.join(temp_dir, f"frame2_{uuid.uuid4()}.webp")
        
        for path in [frame1_path, frame2_path]:
            shutil.copy(source_image_path, path)
        
        event_data = {
            "video_id": "video_123",
            "job_id": "job_123",
            "frames": [
                {
                    "frame_id": "frame_1",
                    "ts": 1.0,
                    "local_path": frame1_path
                },
                {
                    "frame_id": "frame_2",
                    "ts": 2.0,
                    "local_path": frame2_path
                }
            ]
        }
        
        # Mock save_frame_mask to return valid paths and create dummy files
        mock_mask_path_1 = os.path.join(temp_dir, "video_mask_frame_1.png")
        mock_mask_path_2 = os.path.join(temp_dir, "video_mask_frame_2.png")
        
        with patch.object(service.file_manager, 'save_frame_mask', side_effect=[mock_mask_path_1, mock_mask_path_2]) as mock_save:
            with patch('services.service.cv2.imread', return_value=np.ones((100, 100), dtype=np.uint8) * 255):
                # Create dummy mask files for cv2.imread to find
                Image.fromarray(np.ones((100, 100), dtype=np.uint8) * 255, mode='L').save(mock_mask_path_1)
                Image.fromarray(np.ones((100, 100), dtype=np.uint8) * 255, mode='L').save(mock_mask_path_2)
                
                await service.handle_videos_keyframes_ready(event_data)
        
        # Verify segmentation was called for both frames
        assert service.foreground_segmentor.call_count == 2
        
        # Verify database was updated for both frames
        assert service.db.execute.call_count == 2
        
        # Verify event was published via event_emitter
        # Calculate the expected final mask paths based on FileManager's logic
        from config_loader import config
        from pathlib import Path
        expected_mask_path_1_obj = Path(config.PRODUCT_MASK_DIR_PATH) / "frames" / f"{event_data['frames'][0]['frame_id']}.png"
        expected_mask_path_1 = str(expected_mask_path_1_obj)
        expected_mask_path_2_obj = Path(config.PRODUCT_MASK_DIR_PATH) / "frames" / f"{event_data['frames'][1]['frame_id']}.png"
        expected_mask_path_2 = str(expected_mask_path_2_obj)

        service.event_emitter.emit_video_keyframes_masked.assert_called_once_with(
            job_id="job_123",
            video_id="video_123",
            frames=[
                {
                    "frame_id": "frame_1",
                    "ts": 1.0,
                    "mask_path": expected_mask_path_1
                },
                {
                    "frame_id": "frame_2",
                    "ts": 2.0,
                    "mask_path": expected_mask_path_2
                }
            ]
        )
    
    @pytest.mark.asyncio
    async def test_handle_videos_keyframes_ready_batch_empty(self, service):
        """Test handling empty video keyframes batch."""
        await service.initialize()
        
        event_data = {
            "job_id": "job_123",
            "total_keyframes": 0
        }
        
        await service.handle_videos_keyframes_ready_batch(event_data)
        
        # Verify immediate batch completion event was published via event_emitter
        service.event_emitter.emit_videos_keyframes_masked_batch.assert_called_once_with(
            job_id="job_123",
            total_keyframes=0
        )
    
    @pytest.mark.asyncio
    async def test_segmentation_failure_handling(self, service, temp_dir):
        """Test handling of segmentation failures."""
        await service.initialize()
        
        # Use failing segmentor
        failing_segmentor = MockSegmentor(should_fail=True)
        service.foreground_segmentor = failing_segmentor
        service.image_processor.segmentor = failing_segmentor
        
        # Create test image
        source_image_path = os.path.join(os.path.dirname(__file__), 'test_image.webp')
        test_image_path = os.path.join(temp_dir, f"test_image_{uuid.uuid4()}.webp")
        shutil.copy(source_image_path, test_image_path)
        
        event_data = {
            "product_id": "prod_123",
            "image_id": "img_123",
            "local_path": test_image_path,
            "job_id": "job_123"
        }
        
        await service.handle_products_image_ready(event_data)
        
        # Verify no database update or event publication occurred
        service.db.execute.assert_not_called()
        service.broker.publish_event.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_missing_image_file_handling(self, service):
        """Test handling of missing image files."""
        await service.initialize()
        
        # Create a mock segmentor that will fail due to missing file
        failing_segmentor = MockSegmentor(should_fail=True)
        service.foreground_segmentor = failing_segmentor
        service.image_processor.segmentor = failing_segmentor
        
        event_data = {
            "product_id": "prod_123",
            "image_id": "img_123",
            "local_path": "/nonexistent/path.jpg",
            "job_id": "job_123"
        }
        
        await service.handle_products_image_ready(event_data)
        
        # Verify no database update or event publication occurred
        service.db.execute.assert_not_called()
        service.broker.publish_event.assert_not_called()
    


if __name__ == "__main__":
    pytest.main([__file__])