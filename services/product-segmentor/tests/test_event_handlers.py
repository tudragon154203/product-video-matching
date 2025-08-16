"""Tests for event handlers."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from handlers.segmentor_handler import ProductSegmentorHandler


class TestProductSegmentorHandler:
    """Test event handler functionality."""
    
    @pytest.fixture
    def handler(self):
        """Create handler with mocked dependencies."""
        with patch('handlers.segmentor_handler.config') as mock_config:
            mock_config.postgres_dsn = "postgresql://test"
            mock_config.bus_broker = "amqp://test"
            mock_config.segmentation_model_name = "test/model"
            mock_config.mask_base_path = "/tmp/masks"
            mock_config.max_concurrent_images = 2
            
            handler = ProductSegmentorHandler()
            
            # Mock the service
            handler.service = AsyncMock()
            handler.service.initialize = AsyncMock()
            handler.service.cleanup = AsyncMock()
            
            return handler
    
    @pytest.mark.asyncio
    async def test_handler_initialization(self, handler):
        """Test handler initialization."""
        await handler.initialize()
        
        assert handler.initialized
        handler.service.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handler_cleanup(self, handler):
        """Test handler cleanup."""
        await handler.cleanup()
        
        handler.service.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_products_images_ready(self, handler):
        """Test product images ready event handling."""
        await handler.initialize()
        
        event_data = {
            "product_id": "prod_123",
            "image_id": "img_123",
            "local_path": "/path/to/image.jpg",
            "job_id": "job_123"
        }
        
        await handler.handle_products_images_ready(event_data)
        
        handler.service.handle_products_images_ready.assert_called_once_with(event_data)
    
    @pytest.mark.asyncio
    async def test_handle_products_images_ready_batch(self, handler):
        """Test product images ready batch event handling."""
        await handler.initialize()
        
        event_data = {
            "job_id": "job_123",
            "event_id": "event_123",
            "total_images": 5
        }
        
        await handler.handle_products_images_ready_batch(event_data)
        
        handler.service.handle_products_images_ready_batch.assert_called_once_with(event_data)
    
    @pytest.mark.asyncio
    async def test_handle_videos_keyframes_ready(self, handler):
        """Test video keyframes ready event handling."""
        await handler.initialize()
        
        event_data = {
            "video_id": "video_123",
            "job_id": "job_123",
            "frames": [
                {
                    "frame_id": "frame_1",
                    "ts": 1.0,
                    "local_path": "/path/to/frame1.jpg"
                }
            ]
        }
        
        await handler.handle_videos_keyframes_ready(event_data)
        
        handler.service.handle_videos_keyframes_ready.assert_called_once_with(event_data)
    
    @pytest.mark.asyncio
    async def test_handle_videos_keyframes_ready_batch(self, handler):
        """Test video keyframes ready batch event handling."""
        await handler.initialize()
        
        event_data = {
            "job_id": "job_123",
            "event_id": "event_123",
            "total_keyframes": 10
        }
        
        await handler.handle_videos_keyframes_ready_batch(event_data)
        
        handler.service.handle_videos_keyframes_ready_batch.assert_called_once_with(event_data)
    
    @pytest.mark.asyncio
    async def test_error_handling_in_handler(self, handler):
        """Test error handling in event handlers."""
        await handler.initialize()
        
        # Make service method raise an exception
        handler.service.handle_products_images_ready.side_effect = Exception("Test error")
        
        event_data = {
            "product_id": "prod_123",
            "image_id": "img_123",
            "local_path": "/path/to/image.jpg",
            "job_id": "job_123"
        }
        
        # Handler should propagate the exception
        with pytest.raises(Exception, match="Test error"):
            await handler.handle_products_images_ready(event_data)


if __name__ == "__main__":
    pytest.main([__file__])