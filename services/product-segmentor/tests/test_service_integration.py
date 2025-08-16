"""Integration tests for Product Segmentor Service."""

import pytest
import asyncio
import numpy as np
from unittest.mock import AsyncMock, Mock, patch
import tempfile
import shutil
import uuid
from PIL import Image

from services.service import ProductSegmentorService
from segmentation.interface import SegmentationInterface


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
        return np.ones((100, 100), dtype=np.uint8) * 255
    
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
        service = ProductSegmentorService(
            db=mock_db,
            broker=mock_broker,
            mask_base_path=temp_dir,
            max_concurrent=2
        )
        
        # Replace segmentor with mock
        service.segmentor = MockSegmentor()
        
        return service
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """Test service initialization."""
        await service.initialize()
        
        assert service.initialized
        assert service.segmentor.is_initialized
    
    @pytest.mark.asyncio
    async def test_service_initialization_failure(self, service):
        """Test service initialization failure."""
        service.segmentor = MockSegmentor(should_fail=True)
        
        with pytest.raises(Exception):
            await service.initialize()
        
        assert not service.initialized
    
    @pytest.mark.asyncio
    async def test_handle_products_images_ready(self, service, temp_dir):
        """Test handling product images ready event."""
        await service.initialize()
        
        # Create test image
        test_image_path = f"{temp_dir}/test_image.jpg"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(test_image_path)
        
        event_data = {
            "product_id": "prod_123",
            "image_id": "img_123",
            "local_path": test_image_path,
            "job_id": "job_123"
        }
        
        with patch.object(service.file_manager, 'save_product_mask', return_value="/mask/path.png") as mock_save:
            await service.handle_products_images_ready(event_data)
        
        # Verify segmentation was called
        assert service.segmentor.call_count == 1
        
        # Verify mask was saved
        mock_save.assert_called_once()
        
        # Verify database was updated
        service.db.execute.assert_called_once()
        
        # Verify event was published
        service.broker.publish_event.assert_called_once_with(
            "products.image.masked",
            {
                "event_id": any(str),
                "job_id": "job_123",
                "image_id": "img_123",
                "mask_path": "/mask/path.png"
            }
        )
    
    @pytest.mark.asyncio
    async def test_handle_products_images_ready_batch_empty(self, service):
        """Test handling empty product images batch."""
        await service.initialize()
        
        event_data = {
            "job_id": "job_123",
            "total_images": 0
        }
        
        await service.handle_products_images_ready_batch(event_data)
        
        # Verify immediate completion event was published
        service.broker.publish_event.assert_called_once_with(
            "products.images.masked.batch",
            {
                "event_id": any(str),
                "job_id": "job_123",
                "total_images": 0
            }
        )
    
    @pytest.mark.asyncio
    async def test_handle_videos_keyframes_ready(self, service, temp_dir):
        """Test handling video keyframes ready event."""
        await service.initialize()
        
        # Create test images for frames
        frame1_path = f"{temp_dir}/frame1.jpg"
        frame2_path = f"{temp_dir}/frame2.jpg"
        
        for path in [frame1_path, frame2_path]:
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(path)
        
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
        
        with patch.object(service.file_manager, 'save_frame_mask', side_effect=["/mask1.png", "/mask2.png"]):
            await service.handle_videos_keyframes_ready(event_data)
        
        # Verify segmentation was called for both frames
        assert service.segmentor.call_count == 2
        
        # Verify database was updated for both frames
        assert service.db.execute.call_count == 2
        
        # Verify event was published with both frames
        service.broker.publish_event.assert_called_once_with(
            "video.keyframes.masked",
            {
                "event_id": any(str),
                "job_id": "job_123",
                "video_id": "video_123",
                "frames": [
                    {
                        "frame_id": "frame_1",
                        "ts": 1.0,
                        "mask_path": "/mask1.png"
                    },
                    {
                        "frame_id": "frame_2",
                        "ts": 2.0,
                        "mask_path": "/mask2.png"
                    }
                ]
            }
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
        
        # Verify immediate completion event was published
        service.broker.publish_event.assert_called_once_with(
            "video.keyframes.masked.batch",
            {
                "event_id": any(str),
                "job_id": "job_123",
                "total_keyframes": 0
            }
        )
    
    @pytest.mark.asyncio
    async def test_segmentation_failure_handling(self, service, temp_dir):
        """Test handling of segmentation failures."""
        await service.initialize()
        
        # Use failing segmentor
        service.segmentor = MockSegmentor(should_fail=True)
        
        # Create test image
        test_image_path = f"{temp_dir}/test_image.jpg"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(test_image_path)
        
        event_data = {
            "product_id": "prod_123",
            "image_id": "img_123",
            "local_path": test_image_path,
            "job_id": "job_123"
        }
        
        await service.handle_products_images_ready(event_data)
        
        # Verify no database update or event publication occurred
        service.db.execute.assert_not_called()
        service.broker.publish_event.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_missing_image_file_handling(self, service):
        """Test handling of missing image files."""
        await service.initialize()
        
        event_data = {
            "product_id": "prod_123",
            "image_id": "img_123",
            "local_path": "/nonexistent/path.jpg",
            "job_id": "job_123"
        }
        
        await service.handle_products_images_ready(event_data)
        
        # Verify no database update or event publication occurred
        service.db.execute.assert_not_called()
        service.broker.publish_event.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_service_cleanup(self, service):
        """Test service cleanup."""
        await service.initialize()
        
        # Add some batch trackers
        service._batch_trackers["job1"] = Mock()
        service._batch_trackers["job2"] = Mock()
        
        await service.cleanup()
        
        # Verify cleanup
        assert not service.initialized
        assert len(service._batch_trackers) == 0
        assert not service.segmentor.is_initialized


if __name__ == "__main__":
    pytest.main([__file__])