from unittest.mock import Mock, AsyncMock, patch
import pytest
from services.keypoint_asset_processor import KeypointAssetProcessor


class TestKeypointAssetProcessor:
    """Unit tests for KeypointAssetProcessor class"""

    def setup_method(self):
        """Setup for each test"""
        self.mock_db = Mock()
        self.mock_broker = Mock()
        self.mock_extractor = Mock()

        # Create a proper mock for progress manager with expected attributes
        self.mock_progress_manager = Mock()
        self.mock_progress_manager.processed_assets = set()
        self.mock_progress_manager.job_tracking = {}
        self.mock_progress_manager.job_image_counts = {}
        self.mock_progress_manager.job_frame_counts = {}
        self.mock_progress_manager.expected_total_frames = {}

        # Create the asset processor instance
        self.processor = KeypointAssetProcessor(
            self.mock_db,
            self.mock_broker,
            self.mock_extractor,
            self.mock_progress_manager
        )

    @pytest.mark.unit
    @patch('services.keypoint_asset_processor.uuid.uuid4')
    async def test_process_single_asset_success_non_masked(self, mock_uuid):
        """Test successful processing of a single non-masked asset"""
        # Setup
        mock_uuid.return_value = "test-uuid-123"
        self.mock_extractor.extract_keypoints = AsyncMock(return_value="/path/to/keypoints.npz")
        self.mock_progress_manager.processed_assets = set()
        self.mock_db.execute = AsyncMock()
        self.mock_broker.publish_event = AsyncMock()

        # Call the method
        result = await self.processor.process_single_asset(
            job_id="job_123",
            asset_id="asset_456",
            asset_type="image",
            local_path="/path/to/image.jpg",
            is_masked=False,
            mask_path=None
        )

        # Assertions
        assert result is True
        self.mock_extractor.extract_keypoints.assert_called_once_with("/path/to/image.jpg", "asset_456")
        self.mock_db.execute.assert_called_once()
        self.mock_broker.publish_event.assert_called_once_with(
            topic="image.keypoint.ready",
            event_data={
                "job_id": "job_123",
                "asset_id": "asset_456",
                "event_id": "test-uuid-123",
            }
        )

    @pytest.mark.unit
    @patch('services.keypoint_asset_processor.uuid.uuid4')
    async def test_process_single_asset_success_masked_image(self, mock_uuid):
        """Test successful processing of a single masked image asset"""
        # Setup
        mock_uuid.return_value = "test-uuid-456"
        self.mock_extractor.extract_keypoints_with_mask = AsyncMock(return_value="/path/to/keypoints.npz")
        self.mock_progress_manager.processed_assets = set()
        self.mock_db.execute = AsyncMock()
        self.mock_broker.publish_event = AsyncMock()
        self.mock_db.fetch_one = AsyncMock(return_value={"local_path": "/original/image.jpg"})

        # Call the method
        result = await self.processor.process_single_asset(
            job_id="job_789",
            asset_id="img_101",
            asset_type="image",
            local_path=None,
            is_masked=True,
            mask_path="/path/to/mask.png"
        )

        # Assertions
        assert result is True
        self.mock_db.fetch_one.assert_called_once_with(
            "SELECT local_path FROM product_images WHERE img_id = $1",
            "img_101"
        )
        self.mock_extractor.extract_keypoints_with_mask.assert_called_once_with(
            "/original/image.jpg", "/path/to/mask.png", "img_101"
        )
        self.mock_db.execute.assert_called_once()
        self.mock_broker.publish_event.assert_called_once()

    @pytest.mark.unit
    @patch('services.keypoint_asset_processor.uuid.uuid4')
    async def test_process_single_asset_success_masked_video(self, mock_uuid):
        """Test successful processing of a single masked video asset"""
        # Setup
        mock_uuid.return_value = "test-uuid-789"
        self.mock_extractor.extract_keypoints_with_mask = AsyncMock(return_value="/path/to/keypoints.npz")
        self.mock_progress_manager.processed_assets = set()
        self.mock_db.execute = AsyncMock()
        self.mock_broker.publish_event = AsyncMock()
        self.mock_db.fetch_one = AsyncMock(return_value={"local_path": "/original/frame.jpg"})

        # Call the method
        result = await self.processor.process_single_asset(
            job_id="job_abc",
            asset_id="frame_202",
            asset_type="video",
            local_path=None,
            is_masked=True,
            mask_path="/path/to/mask.png"
        )

        # Assertions
        assert result is True
        self.mock_db.fetch_one.assert_called_once_with(
            "SELECT local_path FROM video_frames WHERE frame_id = $1",
            "frame_202"
        )
        self.mock_extractor.extract_keypoints_with_mask.assert_called_once_with(
            "/original/frame.jpg", "/path/to/mask.png", "frame_202"
        )
        self.mock_db.execute.assert_called_once()
        self.mock_broker.publish_event.assert_called_once()

    @pytest.mark.unit
    async def test_process_single_asset_duplicate(self):
        """Test processing a duplicate asset (should skip)"""
        # Setup with duplicate asset in processed set
        self.mock_progress_manager.processed_assets = {"job_123:asset_456"}

        # Call the method
        result = await self.processor.process_single_asset(
            job_id="job_123",
            asset_id="asset_456",
            asset_type="image",
            local_path="/path/to/image.jpg",
            is_masked=False,
            mask_path=None
        )

        # Assertions
        assert result is False
        # Extractor should not be called for duplicate asset
        self.mock_extractor.extract_keypoints.assert_not_called()

    @pytest.mark.unit
    async def test_process_single_asset_masked_missing_resource(self):
        """Test processing a masked asset when the original resource is missing"""
        # Setup
        self.mock_progress_manager.processed_assets = set()
        self.mock_db.fetch_one = AsyncMock(return_value=None)  # Simulate missing resource

        # Call the method
        result = await self.processor.process_single_asset(
            job_id="job_xyz",
            asset_id="img_missing",
            asset_type="image",
            local_path=None,
            is_masked=True,
            mask_path="/path/to/mask.png"
        )

        # Assertions
        assert result is False
        self.mock_db.fetch_one.assert_called_once()
        # Extractor should not be called if resource not found
        self.mock_extractor.extract_keypoints_with_mask.assert_not_called()

    @pytest.mark.unit
    async def test_process_single_asset_extraction_fails(self):
        """Test processing when keypoint extraction fails"""
        # Setup
        self.mock_progress_manager.processed_assets = set()
        self.mock_extractor.extract_keypoints = AsyncMock(return_value=None)  # Simulate failure

        # Call the method
        result = await self.processor.process_single_asset(
            job_id="job_fail",
            asset_id="asset_fail",
            asset_type="image",
            local_path="/path/to/image.jpg",
            is_masked=False,
            mask_path=None
        )

        # Assertions
        assert result is False
        self.mock_extractor.extract_keypoints.assert_called_once()
        # DB execute and broker publish should not be called on failure
        self.mock_db.execute.assert_not_called()
        self.mock_broker.publish_event.assert_not_called()

    @pytest.mark.unit
    async def test_update_and_check_completion_per_asset_first_image(self):
        """Test updating progress and checking completion for image assets"""
        # Setup
        self.mock_progress_manager.job_tracking = {"job_img": {"image": {"expected": 10, "completed": 0}}}
        self.mock_progress_manager._is_batch_initialized = Mock(return_value=False)
        self.mock_progress_manager.update_job_progress = AsyncMock()

        # Call the method
        await self.processor.update_and_check_completion_per_asset_first("job_img", "image")

        # Assertions
        self.mock_progress_manager.update_job_progress.assert_called_once()

    @pytest.mark.unit
    async def test_update_and_check_completion_per_asset_first_video(self):
        """Test updating progress and checking completion for video assets"""
        # Setup
        self.mock_progress_manager.job_tracking = {"job_vid": {"video": {"expected": 20, "completed": 0}}}
        self.mock_progress_manager._is_batch_initialized = Mock(return_value=True)
        self.mock_progress_manager.expected_total_frames = {"job_vid": 20}
        self.mock_progress_manager.update_job_progress = AsyncMock()
        self.mock_progress_manager.update_expected_and_recheck_completion = AsyncMock()

        # Call the method
        await self.processor.update_and_check_completion_per_asset_first("job_vid", "video")

        # Assertions
        self.mock_progress_manager.update_job_progress.assert_called_once()
        self.mock_progress_manager.update_expected_and_recheck_completion.assert_called_once()

    @pytest.mark.unit
    async def test_handle_batch_initialization_image(self):
        """Test handling batch initialization for image assets"""
        # Setup
        self.mock_progress_manager.job_image_counts = {}
        self.mock_progress_manager._mark_batch_initialized = Mock()
        self.mock_progress_manager.initialize_with_high_expected = AsyncMock()
        self.mock_progress_manager.update_job_progress = AsyncMock()
        self.mock_progress_manager.update_expected_and_recheck_completion = AsyncMock()

        # Call the method
        await self.processor.handle_batch_initialization(
            job_id="batch_job",
            asset_type="image",
            total_items=5,
            event_type="test_event"
        )

        # Assertions
        assert self.mock_progress_manager.job_image_counts["batch_job"]["total"] == 5
        self.mock_progress_manager._mark_batch_initialized.assert_called_once_with("batch_job", "image")

    @pytest.mark.unit
    async def test_handle_batch_initialization_video(self):
        """Test handling batch initialization for video assets"""
        # Setup
        self.mock_progress_manager.expected_total_frames = {}
        self.mock_progress_manager.job_frame_counts = {}
        self.mock_progress_manager._mark_batch_initialized = Mock()
        self.mock_progress_manager.initialize_with_high_expected = AsyncMock()
        self.mock_progress_manager.update_job_progress = AsyncMock()
        self.mock_progress_manager.update_expected_and_recheck_completion = AsyncMock()

        # Call the method
        await self.processor.handle_batch_initialization(
            job_id="batch_job_vid",
            asset_type="video",
            total_items=8,
            event_type="test_event"
        )

        # Assertions
        assert self.mock_progress_manager.expected_total_frames["batch_job_vid"] == 8
        assert self.mock_progress_manager.job_frame_counts["batch_job_vid"]["total"] == 8
        self.mock_progress_manager._mark_batch_initialized.assert_called_once_with("batch_job_vid", "video")

    @pytest.mark.unit
    async def test_handle_batch_initialization_zero_assets(self):
        """Test handling batch initialization for zero asset job"""
        # Setup - job should NOT be in job_tracking to trigger initialize_with_high_expected
        self.mock_progress_manager.job_tracking = {}
        self.mock_progress_manager._mark_batch_initialized = Mock()
        self.mock_progress_manager.initialize_with_high_expected = AsyncMock()
        self.mock_progress_manager.update_job_progress = AsyncMock()
        self.mock_progress_manager.update_expected_and_recheck_completion = AsyncMock()

        # Call the method
        await self.processor.handle_batch_initialization(
            job_id="zero_job",
            asset_type="image",
            total_items=0,
            event_type="test_event"
        )

        # Assertions - initialize_with_high_expected should be called for zero-asset job when tracking doesn't exist
        self.mock_progress_manager.initialize_with_high_expected.assert_called_once_with("zero_job", "image", 0, event_type_prefix="keypoints")
        self.mock_progress_manager.update_job_progress.assert_called_once()
