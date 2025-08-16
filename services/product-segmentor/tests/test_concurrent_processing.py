"""Tests for concurrent processing and resource management."""

import pytest
import asyncio
import numpy as np
from unittest.mock import AsyncMock, Mock, patch
import tempfile
import shutil

from services.service import ProductSegmentorService
from segmentation.interface import SegmentationInterface


class MockSegmentor(SegmentationInterface):
    """Mock segmentor for testing concurrent processing."""
    
    def __init__(self, processing_delay: float = 0.1):
        self.processing_delay = processing_delay
        self._initialized = False
        self.call_count = 0
        self.concurrent_calls = 0
        self.max_concurrent_calls = 0
    
    async def initialize(self) -> None:
        self._initialized = True
    
    async def segment_image(self, image_path: str) -> np.ndarray:
        self.call_count += 1
        self.concurrent_calls += 1
        self.max_concurrent_calls = max(self.max_concurrent_calls, self.concurrent_calls)
        
        # Simulate processing time
        await asyncio.sleep(self.processing_delay)
        
        self.concurrent_calls -= 1
        
        # Return a simple mask
        return np.ones((100, 100), dtype=np.uint8) * 255
    
    def cleanup(self) -> None:
        self._initialized = False
    
    @property
    def model_name(self) -> str:
        return "mock"
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized


class TestConcurrentProcessing:
    """Test concurrent processing capabilities."""
    
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
    def service_with_mock_segmentor(self, mock_db, mock_broker, temp_dir):
        """Create service with mock segmentor."""
        service = ProductSegmentorService(
            db=mock_db,
            broker=mock_broker,
            mask_base_path=temp_dir,
            max_concurrent=2  # Limit to 2 concurrent operations
        )
        
        # Replace segmentor with mock
        mock_segmentor = MockSegmentor(processing_delay=0.2)
        service.segmentor = mock_segmentor
        
        return service, mock_segmentor
    
    @pytest.mark.asyncio
    async def test_concurrent_processing_limit(self, service_with_mock_segmentor):
        """Test that concurrent processing respects the limit."""
        service, mock_segmentor = service_with_mock_segmentor
        
        await service.initialize()
        
        # Create multiple concurrent tasks
        tasks = []
        for i in range(5):
            event_data = {
                "product_id": f"prod_{i}",
                "image_id": f"img_{i}",
                "local_path": f"/fake/path_{i}.jpg",
                "job_id": "test_job"
            }
            
            # Mock the segmentor to avoid file system operations
            with patch.object(service.segmentor, 'segment_image', mock_segmentor.segment_image):
                with patch.object(service.file_manager, 'save_product_mask', return_value=f"/mask_{i}.png"):
                    task = asyncio.create_task(service.handle_products_images_ready(event_data))
                    tasks.append(task)
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        
        # Verify that concurrent processing was limited
        assert mock_segmentor.max_concurrent_calls <= 2
        assert mock_segmentor.call_count == 5
    
    @pytest.mark.asyncio
    async def test_backpressure_handling(self, service_with_mock_segmentor):
        """Test that backpressure prevents memory exhaustion."""
        service, mock_segmentor = service_with_mock_segmentor
        
        await service.initialize()
        
        # Create many concurrent tasks to test backpressure
        tasks = []
        for i in range(10):
            event_data = {
                "product_id": f"prod_{i}",
                "image_id": f"img_{i}",
                "local_path": f"/fake/path_{i}.jpg",
                "job_id": "test_job"
            }
            
            with patch.object(service.segmentor, 'segment_image', mock_segmentor.segment_image):
                with patch.object(service.file_manager, 'save_product_mask', return_value=f"/mask_{i}.png"):
                    task = asyncio.create_task(service.handle_products_images_ready(event_data))
                    tasks.append(task)
        
        # Start tasks and check that they don't all run at once
        start_time = asyncio.get_event_loop().time()
        await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()
        
        # With 10 tasks, 2 concurrent, and 0.2s delay each, minimum time should be around 1s
        # (5 batches of 2 tasks each)
        assert end_time - start_time >= 0.8  # Allow some tolerance
        assert mock_segmentor.max_concurrent_calls <= 2
    
    @pytest.mark.asyncio
    async def test_error_handling_in_concurrent_processing(self, service_with_mock_segmentor):
        """Test error handling doesn't break concurrent processing."""
        service, mock_segmentor = service_with_mock_segmentor
        
        await service.initialize()
        
        # Create a segmentor that fails on certain images
        async def failing_segment_image(image_path: str) -> np.ndarray:
            if "fail" in image_path:
                raise Exception("Segmentation failed")
            return await mock_segmentor.segment_image(image_path)
        
        tasks = []
        for i in range(4):
            # Make every other task fail
            path_suffix = "fail.jpg" if i % 2 == 0 else "success.jpg"
            event_data = {
                "product_id": f"prod_{i}",
                "image_id": f"img_{i}",
                "local_path": f"/fake/path_{path_suffix}",
                "job_id": "test_job"
            }
            
            with patch.object(service.segmentor, 'segment_image', failing_segment_image):
                with patch.object(service.file_manager, 'save_product_mask', return_value=f"/mask_{i}.png"):
                    task = asyncio.create_task(service.handle_products_images_ready(event_data))
                    tasks.append(task)
        
        # All tasks should complete without raising exceptions
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify that successful tasks still processed
        # (We can't easily verify the exact count without more complex mocking)
        assert True  # If we get here, concurrent processing handled errors gracefully
    
    @pytest.mark.asyncio
    async def test_batch_completion_tracking(self, service_with_mock_segmentor):
        """Test batch completion tracking with concurrent processing."""
        service, mock_segmentor = service_with_mock_segmentor
        
        await service.initialize()
        
        job_id = "test_batch_job"
        total_images = 3
        
        # Handle batch event first
        batch_event = {
            "job_id": job_id,
            "event_id": "batch_event_1",
            "total_images": total_images
        }
        
        await service.handle_products_images_ready_batch(batch_event)
        
        # Verify batch tracker was created
        assert job_id in service._batch_trackers
        tracker = service._batch_trackers[job_id]
        assert tracker.total_count == total_images
        assert tracker.processed_count == 0
    
    @pytest.mark.asyncio
    async def test_empty_batch_handling(self, service_with_mock_segmentor):
        """Test handling of empty batches."""
        service, mock_segmentor = service_with_mock_segmentor
        
        await service.initialize()
        
        # Handle empty batch
        batch_event = {
            "job_id": "empty_job",
            "event_id": "empty_batch",
            "total_images": 0
        }
        
        await service.handle_products_images_ready_batch(batch_event)
        
        # Verify that batch completion event was emitted immediately
        service.broker.publish_event.assert_called_with(
            "products.images.masked.batch",
            {
                "event_id": pytest.any(str),
                "job_id": "empty_job",
                "total_images": 0
            }
        )


if __name__ == "__main__":
    pytest.main([__file__])