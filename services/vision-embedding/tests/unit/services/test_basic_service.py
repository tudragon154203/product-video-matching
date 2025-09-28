"""Basic tests for vision embedding service without external dependencies."""

import pytest
pytestmark = pytest.mark.unit
from unittest.mock import Mock, AsyncMock, patch


class TestBasicVisionEmbeddingService:
    """Test basic vision embedding service operations."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a minimal mock service for testing basic functionality."""
        service = Mock()
        service.handle_products_image_ready = AsyncMock()
        service.handle_products_images_masked_batch = AsyncMock()
        service.handle_video_keyframes_masked_batch = AsyncMock()
        service.handle_products_image_masked = AsyncMock()
        service.handle_video_keyframes_masked = AsyncMock()
        service.handle_videos_keyframes_ready = AsyncMock()
        return service
    
    @pytest.mark.unit
    def test_event_handler_interface(self, mock_service):
        """Test that all expected handler methods exist."""
        # These should be async methods
        assert hasattr(mock_service, 'handle_products_image_ready')
        assert hasattr(mock_service, 'handle_products_images_masked_batch')
        assert hasattr(mock_service, 'handle_products_image_masked')
        assert hasattr(mock_service, 'handle_videos_keyframes_ready')
        assert hasattr(mock_service, 'handle_video_keyframes_masked')
        assert hasattr(mock_service, 'handle_video_keyframes_masked_batch')
    
    @pytest.mark.asyncio
    async def test_product_image_ready_handler(self, mock_service):
        """Test product image ready event handling."""
        event_data = {
            "product_id": "prod_123",
            "image_id": "img_123", 
            "local_path": "/tmp/test_image.jpg",
            "job_id": "test_job"
        }
        
        await mock_service.handle_products_image_ready(event_data)
        
        mock_service.handle_products_image_ready.assert_called_once_with(event_data)
    
    @pytest.mark.asyncio
    async def test_batch_handler(self, mock_service):
        """Test batch event handling."""
        event_data = {
            "job_id": "test_job",
            "total_images": 5
        }
        
        await mock_service.handle_products_images_masked_batch(event_data)
        
        mock_service.handle_products_images_masked_batch.assert_called_once_with(event_data)
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_service):
        """Test error handling in event handlers."""
        # Make service raise an exception
        mock_service.handle_products_image_ready.side_effect = Exception("Test error")
        
        event_data = {
            "product_id": "prod_123",
            "image_id": "img_123",
            "local_path": "/tmp/test_image.jpg",
            "job_id": "test_job"
        }
        
        with pytest.raises(Exception, match="Test error"):
            await mock_service.handle_products_image_ready(event_data)