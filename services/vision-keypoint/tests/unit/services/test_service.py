import asyncio
from unittest.mock import Mock, AsyncMock, patch

import pytest

from services.service import VisionKeypointService


class TestVisionKeypointService:
    """Unit tests for VisionKeypointService class"""

    def setup_method(self):
        """Setup for each test"""
        self.mock_db = Mock()
        self.mock_broker = Mock()
        self.mock_data_root = "/tmp/test_data"
        
        # Create a mock extractor with async methods
        self.mock_extractor = Mock()
        self.mock_extractor.extract_keypoints = AsyncMock()
        self.mock_extractor.extract_keypoints_with_mask = AsyncMock()
        
        # Create a mock progress manager
        self.mock_progress_manager = Mock()
        self.mock_progress_manager.cleanup_all = AsyncMock()
        
        # Create a mock asset processor
        self.mock_asset_processor = Mock()
        self.mock_asset_processor.process_single_asset = AsyncMock()
        self.mock_asset_processor.update_and_check_completion_per_asset_first = AsyncMock()
        self.mock_asset_processor.handle_batch_initialization = AsyncMock()
        
        # Create the service instance
        self.service = VisionKeypointService(self.mock_db, self.mock_broker, self.mock_data_root)
        # Override internal components with mocks to avoid complex initialization
        self.service.extractor = self.mock_extractor
        self.service.progress_manager = self.mock_progress_manager
        self.service.asset_processor = self.mock_asset_processor

    @pytest.mark.unit
    async def test_cleanup(self):
        """Test the cleanup method"""
        # Mock the cleanup method
        self.mock_progress_manager.cleanup_all = AsyncMock()
        self.service.progress_manager = self.mock_progress_manager
        
        # Call the method
        await self.service.cleanup()
        
        # Assert that cleanup was called
        self.mock_progress_manager.cleanup_all.assert_called_once()

    @pytest.mark.unit
    async def test_handle_products_image_ready_success(self):
        """Test successful handling of products image ready event"""
        # Setup test data
        event_data = {
            "job_id": "job_123",
            "image_id": "img_456",
            "local_path": "/path/to/image.jpg"
        }
        
        # Mock the process_single_asset to return True (success)
        self.mock_asset_processor.process_single_asset.return_value = True
        self.service.asset_processor = self.mock_asset_processor
        
        # Call the method
        await self.service.handle_products_image_ready(event_data)
        
        # Assert that process_single_asset was called with correct parameters
        self.mock_asset_processor.process_single_asset.assert_called_once_with(
            "job_123",
            "img_456",
            "image",
            "/path/to/image.jpg",
        )
        
        # Assert that update_progress was called
        self.mock_asset_processor.update_and_check_completion_per_asset_first.assert_called_once_with(
            "job_123", "image"
        )

    @pytest.mark.unit
    async def test_handle_products_image_ready_failure(self):
        """Test handling of products image ready event when processing fails"""
        # Setup test data
        event_data = {
            "job_id": "job_123",
            "image_id": "img_456",
            "local_path": "/path/to/image.jpg"
        }
        
        # Mock the process_single_asset to return False (failure)
        self.mock_asset_processor.process_single_asset.return_value = False
        self.service.asset_processor = self.mock_asset_processor
        
        # Call the method
        await self.service.handle_products_image_ready(event_data)
        
        # Assert that process_single_asset was called
        self.mock_asset_processor.process_single_asset.assert_called_once()
        
        # Since processing failed, update_progress should not be called
        self.mock_asset_processor.update_and_check_completion_per_asset_first.assert_not_called()

    @pytest.mark.unit
    async def test_handle_videos_keyframes_ready_success(self):
        """Test successful handling of video keyframes ready event"""
        # Setup test data
        event_data = {
            "job_id": "job_789",
            "frames": [
                {"frame_id": "frame_001", "local_path": "/path/to/frame1.jpg"},
                {"frame_id": "frame_002", "local_path": "/path/to/frame2.jpg"}
            ]
        }
        
        # Mock the process_single_asset to return True (success)
        self.mock_asset_processor.process_single_asset.return_value = True
        self.service.asset_processor = self.mock_asset_processor
        
        # Call the method
        await self.service.handle_videos_keyframes_ready(event_data)
        
        # Assert that process_single_asset was called twice (once for each frame)
        assert self.mock_asset_processor.process_single_asset.call_count == 2
        
        # Assert that update_progress was called twice
        assert self.mock_asset_processor.update_and_check_completion_per_asset_first.call_count == 2

    @pytest.mark.unit
    async def test_handle_products_image_masked_success(self):
        """Test successful handling of products image masked event"""
        # Setup test data
        event_data = {
            "job_id": "job_abc",
            "image_id": "img_def",
            "mask_path": "/path/to/mask.png"
        }
        
        # Mock the process_single_asset to return True (success)
        self.mock_asset_processor.process_single_asset.return_value = True
        self.service.asset_processor = self.mock_asset_processor
        
        # Call the method
        await self.service.handle_products_image_masked(event_data)
        
        # Verify the call to process_single_asset included the masked parameters
        self.mock_asset_processor.process_single_asset.assert_called_once_with(
            "job_abc",
            "img_def",
            "image",
            None,  # local_path is None for masked processing
            is_masked=True,
            mask_path="/path/to/mask.png"
        )
        
        # Verify that update progress was called
        self.mock_asset_processor.update_and_check_completion_per_asset_first.assert_called_once_with(
            "job_abc", "image"
        )

    @pytest.mark.unit
    async def test_handle_video_keyframes_masked_success(self):
        """Test successful handling of video keyframes masked event"""
        # Setup test data
        event_data = {
            "job_id": "job_ghi",
            "frames": [
                {"frame_id": "frame_111", "mask_path": "/path/to/mask1.png"},
                {"frame_id": "frame_222", "mask_path": "/path/to/mask2.png"}
            ]
        }
        
        # Mock the process_single_asset to return True (success)
        self.mock_asset_processor.process_single_asset.return_value = True
        self.service.asset_processor = self.mock_asset_processor
        
        # Call the method
        await self.service.handle_video_keyframes_masked(event_data)
        
        # Verify that process_single_asset was called twice (once for each frame)
        assert self.mock_asset_processor.process_single_asset.call_count == 2
        
        # Verify that update progress was called twice
        assert self.mock_asset_processor.update_and_check_completion_per_asset_first.call_count == 2

    @pytest.mark.unit
    async def test_handle_products_images_masked_batch(self):
        """Test handling of products images masked batch event"""
        # Setup test data
        event_data = {
            "job_id": "job_jkl",
            "total_images": 10
        }
        
        # Call the method
        await self.service.handle_products_images_masked_batch(event_data)
        
        # Verify the call to handle batch initialization
        self.mock_asset_processor.handle_batch_initialization.assert_called_once_with(
            "job_jkl",
            "image",
            10,
            "products_images_masked_batch",
        )

    @pytest.mark.unit
    async def test_handle_videos_keyframes_masked_batch_new_event(self):
        """Test handling of videos keyframes masked batch event for a new event"""
        # Setup test data
        event_data = {
            "job_id": "job_mno",
            "event_id": "event_123",
            "total_keyframes": 5
        }
        
        # Create a mock for processed_batch_events set
        self.service.progress_manager.processed_batch_events = set()
        
        # Call the method
        await self.service.handle_videos_keyframes_masked_batch(event_data)
        
        # Verify the call to handle batch initialization
        self.mock_asset_processor.handle_batch_initialization.assert_called_once_with(
            "job_mno",
            "video",
            5,
            "videos_keyframes_masked_batch",
            "event_123"
        )
        
        # Verify the event was added to processed_batch_events
        assert "job_mno:event_123" in self.service.progress_manager.processed_batch_events

    @pytest.mark.unit
    async def test_handle_videos_keyframes_masked_batch_duplicate_event(self):
        """Test handling of videos keyframes masked batch event for a duplicate event"""
        # Setup test data
        event_data = {
            "job_id": "job_pqr",
            "event_id": "event_456",
            "total_keyframes": 8
        }
        
        # Add the event to processed_batch_events to simulate a duplicate
        self.service.progress_manager.processed_batch_events = {"job_pqr:event_456"}
        
        # Call the method
        await self.service.handle_videos_keyframes_masked_batch(event_data)
        
        # Verify that handle_batch_initialization was NOT called for duplicate event
        self.mock_asset_processor.handle_batch_initialization.assert_not_called()