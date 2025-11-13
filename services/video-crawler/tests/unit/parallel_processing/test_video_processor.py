"""
Unit tests for enhanced VideoProcessor with idempotency.

Tests the updated video processor that integrates with the idempotency manager
and supports parallel processing operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.video_processor import VideoProcessor
from services.idempotency_manager import IdempotencyManager


class TestVideoProcessorInitialization:
    """Test VideoProcessor initialization and configuration."""

    def test_processor_initialization_basic(self, mock_db):
        """Test basic processor initialization."""
        processor = VideoProcessor(mock_db)

        assert processor.db == mock_db
        assert processor.event_emitter is None
        assert processor.job_progress_manager is None
        assert processor.idempotency_manager is not None
        assert isinstance(processor.idempotency_manager, IdempotencyManager)

    def test_processor_initialization_with_components(self, mock_db, mock_event_emitter, mock_progress_manager):
        """Test processor initialization with all components."""
        processor = VideoProcessor(
            db=mock_db,
            event_emitter=mock_event_emitter,
            job_progress_manager=mock_progress_manager,
            video_dir_override="/custom/path"
        )

        assert processor.event_emitter == mock_event_emitter
        assert processor.job_progress_manager == mock_progress_manager
        assert processor._video_dir_override == "/custom/path"

    def test_processor_initialization_with_custom_idempotency_manager(self, mock_db):
        """Test processor initialization with custom idempotency manager."""
        custom_manager = IdempotencyManager(mock_db)
        processor = VideoProcessor(mock_db, idempotency_manager=custom_manager)

        assert processor.idempotency_manager == custom_manager


class TestVideoRecordCreation:
    """Test video record creation with idempotency."""

    @pytest.mark.asyncio
    async def test_create_and_save_video_record_new(self, video_processor, mock_db, sample_video_data):
        """Test creating new video record."""
        # Mock idempotency manager for new video
        video_processor.idempotency_manager.create_video_with_idempotency = AsyncMock(
            return_value=(True, "new_video_id")
        )

        video, created_new = await video_processor._create_and_save_video_record(
            sample_video_data, "test_job"
        )

        assert created_new is True
        assert video.video_id == "new_video_id"
        assert video.platform == sample_video_data["platform"]
        assert video.url == sample_video_data["url"]
        assert video.title == sample_video_data["title"]

    @pytest.mark.asyncio
    async def test_create_and_save_video_record_existing(self, video_processor, mock_db, sample_video_data):
        """Test handling existing video record."""
        # Mock idempotency manager for existing video
        video_processor.idempotency_manager.create_video_with_idempotency = AsyncMock(
            return_value=(False, "existing_video_id")
        )

        video, created_new = await video_processor._create_and_save_video_record(
            sample_video_data, "test_job"
        )

        assert created_new is False
        assert video.video_id == "existing_video_id"

    @pytest.mark.asyncio
    async def test_create_and_save_video_record_no_video_id(self, video_processor, mock_db):
        """Test creating video record without existing video_id."""
        video_data_without_id = {
            "platform": "youtube",
            "url": "https://example.com/video",
            "title": "Test Video"
        }

        video_processor.idempotency_manager.create_video_with_idempotency = AsyncMock(
            return_value=(True, "generated_video_id")
        )

        video, created_new = await video_processor._create_and_save_video_record(
            video_data_without_id, "test_job"
        )

        assert created_new is True
        assert video.video_id == "generated_video_id"


class TestKeyframeSaving:
    """Test keyframe saving with idempotency."""

    @pytest.mark.asyncio
    async def test_save_keyframes_new_frames(self, video_processor, sample_keyframes):
        """Test saving new keyframes."""
        video_id = "test_video"

        # Mock idempotency manager for new frames
        video_processor.idempotency_manager.create_frame_with_idempotency = AsyncMock(
            side_effect=[
                (True, f"{video_id}_frame_0"),
                (True, f"{video_id}_frame_1"),
                (True, f"{video_id}_frame_2")
            ]
        )

        frame_data = await video_processor._save_keyframes(sample_keyframes, video_id)

        assert len(frame_data) == 3
        assert frame_data[0]["frame_id"] == f"{video_id}_frame_0"
        assert frame_data[0]["ts"] == 0.0
        assert frame_data[0]["local_path"] == "/path/to/frame_0.jpg"

    @pytest.mark.asyncio
    async def test_save_keyframes_existing_frames(self, video_processor, sample_keyframes):
        """Test saving keyframes when some already exist."""
        video_id = "test_video"

        # Mock idempotency manager with mix of new and existing frames
        video_processor.idempotency_manager.create_frame_with_idempotency = AsyncMock(
            side_effect=[
                (True, f"{video_id}_frame_0"),  # New frame
                (False, f"{video_id}_frame_1"),  # Existing frame
                (True, f"{video_id}_frame_2")   # New frame
            ]
        )

        # Mock get_existing_frames for the existing frame
        existing_frames = [{"frame_id": f"{video_id}_frame_1", "ts": 5.0, "local_path": "/path/to/frame_1.jpg"}]
        video_processor.idempotency_manager.get_existing_frames = AsyncMock(return_value=existing_frames)

        frame_data = await video_processor._save_keyframes(sample_keyframes, video_id)

        assert len(frame_data) == 3
        assert frame_data[0]["frame_id"] == f"{video_id}_frame_0"  # New
        assert frame_data[1]["frame_id"] == f"{video_id}_frame_1"  # Existing, fetched from DB
        assert frame_data[2]["frame_id"] == f"{video_id}_frame_2"  # New

    @pytest.mark.asyncio
    async def test_save_keyframes_empty_list(self, video_processor):
        """Test saving empty keyframes list."""
        frame_data = await video_processor._save_keyframes([], "test_video")
        assert frame_data == []


class TestVideoProcessing:
    """Test main video processing functionality."""

    @pytest.mark.asyncio
    async def test_process_video_new_video_new_frames(self, video_processor, sample_video_data, mock_event_emitter):
        """Test processing new video with new frames."""
        # Mock successful video and frame creation
        video_processor.idempotency_manager.create_video_with_idempotency = AsyncMock(return_value=(True, "video_123"))
        video_processor.idempotency_manager.get_existing_frames = AsyncMock(return_value=[])
        video_processor._process_standard_video = AsyncMock(return_value=[
            {"frame_id": "video_123_frame_0", "ts": 0.0, "local_path": "/path/frame_0.jpg"}
        ])
        video_processor._emit_keyframes_ready_event = AsyncMock()
        video_processor._update_progress = AsyncMock()

        result = await video_processor.process_video(sample_video_data, "test_job")

        assert result["video_id"] == "video_123"
        assert result["platform"] == sample_video_data["platform"]
        assert len(result["frames"]) == 1
        assert result["created_new"] is True

    @pytest.mark.asyncio
    async def test_process_video_existing_video_with_frames(self, video_processor, sample_video_data):
        """Test processing existing video that already has frames."""
        # Mock existing video with frames
        video_processor.idempotency_manager.create_video_with_idempotency = AsyncMock(return_value=(False, "existing_video"))
        video_processor.idempotency_manager.get_existing_frames = AsyncMock(return_value=[
            {"frame_id": "existing_video_frame_0", "ts": 0.0, "local_path": "/path/frame_0.jpg"}
        ])
        video_processor._update_progress = AsyncMock()

        result = await video_processor.process_video(sample_video_data, "test_job")

        assert result["video_id"] == "existing_video"
        assert result["skipped"] is True
        assert len(result["frames"]) == 1
        # Note: Processing methods should not be called, but we can't assert on actual methods

    @pytest.mark.asyncio
    async def test_process_video_existing_video_no_frames(self, video_processor, sample_video_data, mock_event_emitter):
        """Test processing existing video that has no frames yet."""
        # Mock existing video without frames
        video_processor.idempotency_manager.create_video_with_idempotency = AsyncMock(return_value=(False, "existing_video"))
        video_processor.idempotency_manager.get_existing_frames = AsyncMock(return_value=[])
        video_processor._process_standard_video = AsyncMock(return_value=[
            {"frame_id": "existing_video_frame_0", "ts": 0.0, "local_path": "/path/frame_0.jpg"}
        ])
        video_processor._emit_keyframes_ready_event = AsyncMock()
        video_processor._update_progress = AsyncMock()

        result = await video_processor.process_video(sample_video_data, "test_job")

        assert result["video_id"] == "existing_video"
        assert result["created_new"] is False
        assert len(result["frames"]) == 1

    @pytest.mark.asyncio
    async def test_process_video_error_handling(self, video_processor, sample_video_data):
        """Test error handling in video processing."""
        # Mock idempotency manager to raise exception
        video_processor.idempotency_manager.create_video_with_idempotency = AsyncMock(
            side_effect=Exception("Database error")
        )

        result = await video_processor.process_video(sample_video_data, "test_job")

        assert result["video_id"] is None
        assert result["frames"] == []
        assert result["platform"] == sample_video_data["platform"]


class TestPlatformSpecificProcessing:
    """Test platform-specific video processing."""

    @pytest.mark.asyncio
    async def test_process_tiktok_video_with_local_path(self, video_processor, sample_video_data):
        """Test processing TikTok video with existing local path."""
        from common_py.models import Video

        video_data = sample_video_data.copy()
        video_data["local_path"] = "/path/to/local/video.mp4"

        video = Video(
            video_id="tiktok_video_123",
            platform="tiktok",
            url=video_data["url"],
            title=video_data["title"]
        )

        # Mock keyframe extraction
        video_processor.keyframe_extractor.extract_keyframes = AsyncMock(return_value=[
            (0.0, "/path/to/frame_0.jpg")
        ])
        video_processor._save_keyframes = AsyncMock(return_value=[
            {"frame_id": "frame_0", "ts": 0.0, "local_path": "/path/to/frame_0.jpg"}
        ])

        result = await video_processor._process_tiktok_video(video, video_data)

        assert len(result) == 1
        assert result[0]["frame_id"] == "frame_0"

    @pytest.mark.asyncio
    async def test_process_standard_video(self, video_processor, sample_video_data):
        """Test processing standard video (YouTube, etc.)."""
        from common_py.models import Video

        video = Video(
            video_id="standard_video_123",
            platform="youtube",
            url=sample_video_data["url"],
            title=sample_video_data["title"]
        )

        # Mock keyframe extraction
        video_processor.keyframe_extractor.extract_keyframes = AsyncMock(return_value=[
            (0.0, "/path/to/frame_0.jpg")
        ])
        video_processor._save_keyframes = AsyncMock(return_value=[
            {"frame_id": "frame_0", "ts": 0.0, "local_path": "/path/to/frame_0.jpg"}
        ])

        result = await video_processor._process_standard_video(video, sample_video_data)

        assert len(result) == 1
        assert result[0]["frame_id"] == "frame_0"

    @pytest.mark.asyncio
    async def test_process_tiktok_video_download_required(self, video_processor, sample_video_data):
        """Test processing TikTok video that requires download."""
        from common_py.models import Video

        video_data = sample_video_data.copy()
        video_data["platform"] = "tiktok"

        video = Video(
            video_id="tiktok_download_123",
            platform="tiktok",
            url=video_data["url"],
            title=video_data["title"]
        )

        # Mock TikTok downloader
        with patch('services.video_processor.TikTokDownloader') as mock_downloader_class:
            mock_downloader = AsyncMock()
            mock_downloader.orchestrate_download_and_extract = AsyncMock(return_value=True)
            mock_downloader_class.return_value = mock_downloader

            # Mock frame crud to return frames
            video_processor.frame_crud.list_video_frames = AsyncMock(return_value=[
                MagicMock(frame_id="frame_0", ts=0.0, local_path="/path/to/frame_0.jpg")
            ])

            result = await video_processor._process_tiktok_video(video, video_data)

            assert len(result) == 1
            assert result[0]["frame_id"] == "frame_0"
            mock_downloader.orchestrate_download_and_extract.assert_called_once()


class TestEventEmissionAndProgress:
    """Test event emission and progress tracking."""

    @pytest.mark.asyncio
    async def test_emit_keyframes_ready_event(self, video_processor, mock_event_emitter, sample_video_data):
        """Test keyframes ready event emission."""
        video_processor.event_emitter = mock_event_emitter

        from common_py.models import Video
        video = Video(
            video_id="test_video",
            platform="youtube",
            url=sample_video_data["url"],
            title=sample_video_data["title"]
        )

        keyframes_data = [
            {"frame_id": "frame_0", "ts": 0.0, "local_path": "/path/to/frame_0.jpg"}
        ]

        await video_processor._emit_keyframes_ready_event(video, keyframes_data, "test_job")

        mock_event_emitter.publish_videos_keyframes_ready.assert_called_once_with(
            "test_video", keyframes_data, "test_job"
        )

    @pytest.mark.asyncio
    async def test_emit_keyframes_ready_event_no_emitter(self, video_processor, sample_video_data):
        """Test keyframes ready event emission with no emitter configured."""
        from common_py.models import Video
        video = Video(
            video_id="test_video",
            platform="youtube",
            url=sample_video_data["url"],
            title=sample_video_data["title"]
        )

        keyframes_data = []

        # Should not raise exception even without emitter
        await video_processor._emit_keyframes_ready_event(video, keyframes_data, "test_job")

    @pytest.mark.asyncio
    async def test_update_progress(self, video_processor, mock_progress_manager):
        """Test progress update."""
        video_processor.job_progress_manager = mock_progress_manager

        await video_processor._update_progress("test_job")

        mock_progress_manager.update_job_progress.assert_called_once_with(
            "test_job", "video", 0, 1, "crawling"
        )

    @pytest.mark.asyncio
    async def test_update_progress_no_manager(self, video_processor):
        """Test progress update with no manager configured."""
        # Should not raise exception even without progress manager
        await video_processor._update_progress("test_job")


class TestVideoProcessorIntegration:
    """Integration tests for VideoProcessor."""

    @pytest.mark.asyncio
    async def test_full_processing_workflow_new_video(self, video_processor, sample_video_data, mock_event_emitter):
        """Test complete processing workflow for new video."""
        video_processor.event_emitter = mock_event_emitter

        # Setup all mocks for successful processing
        video_processor.idempotency_manager.create_video_with_idempotency = AsyncMock(return_value=(True, "video_123"))
        video_processor.idempotency_manager.get_existing_frames = AsyncMock(return_value=[])
        video_processor.keyframe_extractor.extract_keyframes = AsyncMock(return_value=[
            (0.0, "/path/to/frame_0.jpg"),
            (5.0, "/path/to/frame_1.jpg")
        ])
        video_processor._save_keyframes = AsyncMock(return_value=[
            {"frame_id": "video_123_frame_0", "ts": 0.0, "local_path": "/path/to/frame_0.jpg"},
            {"frame_id": "video_123_frame_1", "ts": 5.0, "local_path": "/path/to/frame_1.jpg"}
        ])
        video_processor._emit_keyframes_ready_event = AsyncMock()
        video_processor._update_progress = AsyncMock()

        result = await video_processor.process_video(sample_video_data, "test_job")

        assert result["video_id"] == "video_123"
        assert result["created_new"] is True
        assert len(result["frames"]) == 2

        # Verify all steps were called
        video_processor.idempotency_manager.create_video_with_idempotency.assert_called_once()
        video_processor.keyframe_extractor.extract_keyframes.assert_called_once()
        video_processor._save_keyframes.assert_called_once()
        video_processor._emit_keyframes_ready_event.assert_called_once()
        video_processor._update_progress.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_processing_workflow_existing_video(self, video_processor, sample_video_data):
        """Test complete processing workflow for existing video."""
        # Setup mocks for existing video
        video_processor.idempotency_manager.create_video_with_idempotency = AsyncMock(return_value=(False, "existing_video"))
        video_processor.idempotency_manager.get_existing_frames = AsyncMock(return_value=[
            {"frame_id": "existing_video_frame_0", "ts": 0.0, "local_path": "/path/to/frame_0.jpg"}
        ])
        video_processor._update_progress = AsyncMock()

        result = await video_processor.process_video(sample_video_data, "test_job")

        assert result["video_id"] == "existing_video"
        assert result["skipped"] is True
        assert len(result["frames"]) == 1

        # Verify minimal processing was done
        video_processor.idempotency_manager.create_video_with_idempotency.assert_called_once()
        video_processor.idempotency_manager.get_existing_frames.assert_called_once()
        video_processor._update_progress.assert_called_once()

        # Note: Processing methods should not be called, but we can't assert on actual methods

    @pytest.mark.asyncio
    async def test_processing_error_recovery(self, video_processor, sample_video_data):
        """Test error recovery during processing."""
        # Setup mock to fail during video creation
        video_processor.idempotency_manager.create_video_with_idempotency = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        result = await video_processor.process_video(sample_video_data, "test_job")

        assert result["video_id"] is None
        assert result["frames"] == []
        assert result["platform"] == sample_video_data["platform"]
