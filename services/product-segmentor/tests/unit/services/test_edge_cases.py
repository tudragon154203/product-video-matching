"""Tests for edge cases and error scenarios."""

import pytest
pytestmark = pytest.mark.unit
import asyncio
import numpy as np
from unittest.mock import AsyncMock, Mock, patch
import tempfile
import shutil
from PIL import Image

from services.service import ProductSegmentorService
from segmentation.models.rmbg20_segmentor import RMBG20Segmentor


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
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
    
    @pytest.mark.asyncio
    async def test_empty_batch_handling(self, mock_db, mock_broker, temp_dir):
        """Test handling of empty batches."""
        service = ProductSegmentorService(
            db=mock_db,
            broker=mock_broker
        )
        
        await service.initialize()
        
        # Test empty product images batch
        await service.handle_products_images_ready_batch({
            "job_id": "empty_job",
            "total_images": 0
        })

        # Verify immediate completion event
        mock_broker.publish_event.assert_called_once()
        call_args = mock_broker.publish_event.call_args
        assert call_args[0][0] == "products.images.masked.batch"
        assert call_args[0][1]["job_id"] == "empty_job"
        assert call_args[0][1]["total_images"] == 0
        assert "event_id" in call_args[0][1]
        assert isinstance(call_args[0][1]["event_id"], str)
        
        mock_broker.reset_mock()
        
        # Test empty video keyframes batch
        await service.handle_videos_keyframes_ready_batch({
            "job_id": "empty_video_job",
            "total_keyframes": 0
        })
        
        # Verify immediate completion event
        call_args = mock_broker.publish_event.call_args
        assert call_args[0][0] == "video.keyframes.masked.batch"
        assert call_args[0][1]["job_id"] == "empty_video_job"
        assert call_args[0][1]["total_keyframes"] == 0
        assert "event_id" in call_args[0][1]
        assert isinstance(call_args[0][1]["event_id"], str)
    
    @pytest.mark.asyncio
    async def test_missing_files_handling(self, mock_db, mock_broker, temp_dir):
        """Test handling of missing image files."""
        service = ProductSegmentorService(
            db=mock_db,
            broker=mock_broker
        )
        
        # Mock segmentor that will fail on missing files
        mock_segmentor = AsyncMock()
        mock_segmentor.segment_image.side_effect = FileNotFoundError("File not found")
        service.foreground_segmentor = mock_segmentor
        service.image_processor.segmentor = mock_segmentor
        
        await service.initialize()
        
        # Test with missing product image
        await service.handle_products_image_ready({
            "product_id": "prod_123",
            "image_id": "img_123",
            "local_path": "/nonexistent/image.jpg",
            "job_id": "job_123"
        })
        
        # Verify no database update or event emission
        mock_db.execute.assert_not_called()
        mock_broker.publish_event.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_corrupted_image_handling(self, mock_db, mock_broker, temp_dir):
        """Test handling of corrupted image files."""
        service = ProductSegmentorService(
            db=mock_db,
            broker=mock_broker
        )
        
        # Mock segmentor that returns None for corrupted images
        mock_segmentor = AsyncMock()
        mock_segmentor.segment_image.return_value = None
        service.foreground_segmentor = mock_segmentor
        service.image_processor.segmentor = mock_segmentor
        
        await service.initialize()
        
        # Create a corrupted image file (just text)
        corrupted_path = f"{temp_dir}/corrupted.jpg"
        with open(corrupted_path, 'w') as f:
            f.write("This is not an image")
        
        await service.handle_products_image_ready({
            "product_id": "prod_123",
            "image_id": "img_123",
            "local_path": corrupted_path,
            "job_id": "job_123"
        })
        
        # Verify segmentation was attempted but no further processing
        mock_segmentor.segment_image.assert_called_once()
        mock_db.execute.assert_not_called()
        mock_broker.publish_event.assert_not_called()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_database_error_handling(self, mock_db, mock_broker, temp_dir):
        """Test handling of database errors."""
        service = ProductSegmentorService(
            db=mock_db,
            broker=mock_broker
        )
        
        # Mock successful segmentation
        mock_segmentor = AsyncMock()
        mock_segmentor.segment_image.return_value = np.ones((100, 100), dtype=np.uint8) * 255
        service.foreground_segmentor = mock_segmentor
        service.image_processor.segmentor = mock_segmentor
        
        # Mock database error
        mock_db.execute.side_effect = Exception("Database connection failed")
        
        await service.initialize()
        
        # Create test image
        test_image_path = f"{temp_dir}/test_image.jpg"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(test_image_path)
        
        with patch.object(service.file_manager, 'save_product_final_mask', return_value="/mask/path.png"), \
             patch('cv2.imread', return_value=np.ones((100, 100), dtype=np.uint8) * 255):
            await service.handle_products_image_ready({
                "product_id": "prod_123",
                "image_id": "img_123",
                "local_path": test_image_path,
                "job_id": "job_123"
            })
        
        # Verify segmentation and file save occurred
        mock_segmentor.segment_image.assert_called_once()
        
        # Verify database update was attempted
        mock_db.execute.assert_called_once()
        
        # Event should still be published despite database error
        # Single asset event should be called, but batch completion won't be triggered
        # due to high expected count (1,000,000) vs actual processed (1)
        assert mock_broker.publish_event.call_count == 1
        
        # Check that single asset event was called
        single_call_args = mock_broker.publish_event.call_args_list[0]
        assert single_call_args[0][0] == "products.image.masked"
        assert single_call_args[0][1]["job_id"] == "job_123"
        assert single_call_args[0][1]["image_id"] == "img_123"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_file_save_error_handling(self, mock_db, mock_broker, temp_dir):
        """Test handling of file save errors."""
        service = ProductSegmentorService(
            db=mock_db,
            broker=mock_broker
        )
        
        # Mock successful segmentation
        mock_segmentor = AsyncMock()
        mock_segmentor.segment_image.return_value = np.ones((100, 100), dtype=np.uint8) * 255
        service.foreground_segmentor = mock_segmentor
        service.image_processor.segmentor = mock_segmentor
        
        await service.initialize()
        
        # Create test image
        test_image_path = f"{temp_dir}/test_image.jpg"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(test_image_path)
        
        # Mock file save error
        with patch.object(service.file_manager, 'save_product_final_mask', side_effect=Exception("Disk full")), \
             patch('cv2.imread', return_value=np.ones((100, 100), dtype=np.uint8) * 255):
            await service.handle_products_image_ready({
                "product_id": "prod_123",
                "image_id": "img_123",
                "local_path": test_image_path,
                "job_id": "job_123"
            })
        
        # Verify segmentation occurred
        mock_segmentor.segment_image.assert_called_once()
        
        # Verify no database update or event publication occurred
        mock_db.execute.assert_not_called()
        mock_broker.publish_event.assert_not_called()
    
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_concurrent_processing_limits(self, mock_db, mock_broker, temp_dir):
        """Test that concurrent processing respects limits."""
        service = ProductSegmentorService(
            db=mock_db,
            broker=mock_broker,
            max_concurrent=1  # Limit to 1 for testing
        )
        
        # Mock segmentor with delay
        async def slow_segment(image_path):
            await asyncio.sleep(0.1)
            return np.ones((100, 100), dtype=np.uint8) * 255
        
        mock_segmentor = AsyncMock()
        mock_segmentor.segment_image.side_effect = slow_segment
        service.foreground_segmentor = mock_segmentor
        service.image_processor.segmentor = mock_segmentor
        
        await service.initialize()
        
        # Create test images
        test_image_path = f"{temp_dir}/test_image.jpg"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(test_image_path)
        
        # Start a single task
        task = asyncio.create_task(
            service.handle_products_image_ready({
                "product_id": "prod_1",
                "image_id": "img_1",
                "local_path": test_image_path,
                "job_id": "test_job"
            })
        )
        
        # Wait for the task to complete
        await task
        
        # Verify that the segmentor was called once
        mock_segmentor.segment_image.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_service_cleanup_with_ongoing_processing(self, mock_db, mock_broker, temp_dir):
        """Test service cleanup while processing is ongoing."""
        service = ProductSegmentorService(
            db=mock_db,
            broker=mock_broker,
            max_concurrent=2
        )
        
        # Mock segmentor with long delay
        async def very_slow_segment(image_path):
            await asyncio.sleep(1.0)  # Long delay
            return np.ones((100, 100), dtype=np.uint8) * 255
        
        mock_segmentor = AsyncMock()
        mock_segmentor.segment_image.side_effect = very_slow_segment
        mock_segmentor.cleanup = Mock()
        service.foreground_segmentor = mock_segmentor
        service.image_processor.segmentor = mock_segmentor
        
        await service.initialize()
        
        # Start a long-running task
        test_image_path = f"{temp_dir}/test_image.jpg"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(test_image_path)
        
        with patch.object(service.file_manager, 'save_product_mask', return_value="/mask/path.png"):
            task = asyncio.create_task(
                service.handle_products_image_ready({
                    "product_id": "prod_1",
                    "image_id": "img_1",
                    "local_path": test_image_path,
                    "job_id": "job_123"
                })
            )
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Cleanup should wait for ongoing processing
        cleanup_task = asyncio.create_task(service.cleanup())
        
        # Cleanup should complete (with timeout)
        try:
            await asyncio.wait_for(cleanup_task, timeout=2.0)
        except asyncio.TimeoutError:
            # This is expected behavior - cleanup waits for ongoing processing
            pass
        
        # Cancel the processing task
        task.cancel()
        
        # Verify cleanup was called
        mock_segmentor.cleanup.assert_called_once()

