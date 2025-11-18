"""Unit tests for VideoCrawlerService batch processing logic."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.service import VideoCrawlerService

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_db():
    """Mock database manager."""
    db_mock = MagicMock()
    return db_mock


@pytest.fixture
def mock_broker():
    """Mock message broker."""
    broker_mock = MagicMock()
    broker_mock.publish_event = AsyncMock()
    return broker_mock


@pytest.fixture
def mock_video_processor():
    """Mock video processor."""
    processor = MagicMock()
    processor.process_video = AsyncMock()
    return processor


@pytest.fixture
def mock_cleanup_service():
    """Mock cleanup service."""
    cleanup = MagicMock()
    cleanup.run_auto_cleanup = AsyncMock()
    return cleanup


@pytest.fixture
def mock_event_emitter():
    """Mock event emitter."""
    emitter = MagicMock()
    emitter.publish_videos_keyframes_ready_batch = AsyncMock()
    emitter.publish_videos_collections_completed = AsyncMock()
    return emitter


@pytest.fixture
def service(mock_db, mock_broker):
    """Create VideoCrawlerService instance with mocked dependencies."""
    with patch('services.service.VideoFetcher'), \
         patch('services.service.EventEmitter'), \
         patch('services.service.JobProgressManager'), \
         patch('services.service.VideoProcessor'), \
         patch('services.service.VideoCleanupService'):
        
        service = VideoCrawlerService(
            db=mock_db,
            broker=mock_broker,
            video_dir_override="/test/videos"
        )
        return service


class TestProcessAndEmitVideos:
    """Tests for _process_and_emit_videos method."""

    @pytest.mark.asyncio
    async def test_only_videos_with_frames_included_in_batch(
        self,
        service,
        mock_video_processor,
        mock_cleanup_service,
        mock_event_emitter
    ):
        """Test that only videos with frames are included in batch payload."""
        # Setup
        service.video_processor = mock_video_processor
        service.cleanup_service = mock_cleanup_service
        service.event_emitter = mock_event_emitter
        
        job_id = str(uuid.uuid4())
        correlation_id = job_id
        
        # Mock video processing results - mix of videos with and without frames
        video_results = [
            {"video_id": "video1", "platform": "youtube", "frames": [{"frame_id": "f1", "ts": 10}]},
            {"video_id": "video2", "platform": "youtube", "frames": []},  # No frames
            {"video_id": "video3", "platform": "youtube", "frames": [{"frame_id": "f2", "ts": 20}]},
            {"video_id": "video4", "platform": "youtube", "frames": []},  # No frames
            {"video_id": "video5", "platform": "youtube", "frames": [{"frame_id": "f3", "ts": 30}]},
        ]
        
        mock_video_processor.process_video = AsyncMock(side_effect=video_results)
        
        all_videos = [{"url": f"https://youtube.com/video{i}"} for i in range(5)]
        
        # Execute
        await service._process_and_emit_videos(all_videos, job_id, correlation_id)
        
        # Verify
        # Should only include videos with frames (video1, video3, video5)
        mock_event_emitter.publish_videos_keyframes_ready_batch.assert_called_once()
        call_args = mock_event_emitter.publish_videos_keyframes_ready_batch.call_args
        
        assert call_args[0][0] == job_id  # job_id
        batch_payload = call_args[0][1]  # videos list
        assert len(batch_payload) == 3
        assert batch_payload[0]["video_id"] == "video1"
        assert batch_payload[1]["video_id"] == "video3"
        assert batch_payload[2]["video_id"] == "video5"
        
        # Verify cleanup was called
        mock_cleanup_service.run_auto_cleanup.assert_called_once_with(job_id)
        
        # Verify collections completed was called
        mock_event_emitter.publish_videos_collections_completed.assert_called_once_with(
            job_id, correlation_id
        )

    @pytest.mark.asyncio
    async def test_all_videos_have_frames(
        self,
        service,
        mock_video_processor,
        mock_cleanup_service,
        mock_event_emitter
    ):
        """Test batch processing when all videos have frames."""
        # Setup
        service.video_processor = mock_video_processor
        service.cleanup_service = mock_cleanup_service
        service.event_emitter = mock_event_emitter
        
        job_id = str(uuid.uuid4())
        correlation_id = job_id
        
        # All videos have frames
        video_results = [
            {"video_id": f"video{i}", "platform": "youtube", "frames": [{"frame_id": f"f{i}", "ts": i*10}]}
            for i in range(3)
        ]
        
        mock_video_processor.process_video = AsyncMock(side_effect=video_results)
        
        all_videos = [{"url": f"https://youtube.com/video{i}"} for i in range(3)]
        
        # Execute
        await service._process_and_emit_videos(all_videos, job_id, correlation_id)
        
        # Verify
        mock_event_emitter.publish_videos_keyframes_ready_batch.assert_called_once()
        call_args = mock_event_emitter.publish_videos_keyframes_ready_batch.call_args
        batch_payload = call_args[0][1]
        
        assert len(batch_payload) == 3
        assert all(len(video["frames"]) > 0 for video in batch_payload)

    @pytest.mark.asyncio
    async def test_no_videos_have_frames(
        self,
        service,
        mock_video_processor,
        mock_cleanup_service,
        mock_event_emitter
    ):
        """Test batch processing when no videos have frames."""
        # Setup
        service.video_processor = mock_video_processor
        service.cleanup_service = mock_cleanup_service
        service.event_emitter = mock_event_emitter
        
        job_id = str(uuid.uuid4())
        correlation_id = job_id
        
        # No videos have frames
        video_results = [
            {"video_id": f"video{i}", "platform": "youtube", "frames": []}
            for i in range(3)
        ]
        
        mock_video_processor.process_video = AsyncMock(side_effect=video_results)
        
        all_videos = [{"url": f"https://youtube.com/video{i}"} for i in range(3)]
        
        # Execute
        await service._process_and_emit_videos(all_videos, job_id, correlation_id)
        
        # Verify
        # Batch event should NOT be published when no videos have frames
        mock_event_emitter.publish_videos_keyframes_ready_batch.assert_not_called()
        
        # But collections completed should still be called
        mock_event_emitter.publish_videos_collections_completed.assert_called_once_with(
            job_id, correlation_id
        )

    @pytest.mark.asyncio
    async def test_videos_without_video_id_excluded(
        self,
        service,
        mock_video_processor,
        mock_cleanup_service,
        mock_event_emitter
    ):
        """Test that videos without video_id are excluded from batch."""
        # Setup
        service.video_processor = mock_video_processor
        service.cleanup_service = mock_cleanup_service
        service.event_emitter = mock_event_emitter
        
        job_id = str(uuid.uuid4())
        correlation_id = job_id
        
        # Mix of successful and failed video processing
        video_results = [
            {"video_id": "video1", "platform": "youtube", "frames": [{"frame_id": "f1", "ts": 10}]},
            {"video_id": None, "platform": "youtube", "frames": []},  # Failed processing
            {"video_id": "video3", "platform": "youtube", "frames": [{"frame_id": "f2", "ts": 20}]},
        ]
        
        mock_video_processor.process_video = AsyncMock(side_effect=video_results)
        
        all_videos = [{"url": f"https://youtube.com/video{i}"} for i in range(3)]
        
        # Execute
        await service._process_and_emit_videos(all_videos, job_id, correlation_id)
        
        # Verify
        mock_event_emitter.publish_videos_keyframes_ready_batch.assert_called_once()
        call_args = mock_event_emitter.publish_videos_keyframes_ready_batch.call_args
        batch_payload = call_args[0][1]
        
        # Only videos with video_id AND frames should be included
        assert len(batch_payload) == 2
        assert batch_payload[0]["video_id"] == "video1"
        assert batch_payload[1]["video_id"] == "video3"

    @pytest.mark.asyncio
    async def test_empty_frames_list_excluded(
        self,
        service,
        mock_video_processor,
        mock_cleanup_service,
        mock_event_emitter
    ):
        """Test that videos with empty frames list are excluded."""
        # Setup
        service.video_processor = mock_video_processor
        service.cleanup_service = mock_cleanup_service
        service.event_emitter = mock_event_emitter
        
        job_id = str(uuid.uuid4())
        correlation_id = job_id
        
        # Videos with explicitly empty frames list
        video_results = [
            {"video_id": "video1", "platform": "youtube", "frames": [{"frame_id": "f1", "ts": 10}]},
            {"video_id": "video2", "platform": "youtube", "frames": []},  # Empty list
            {"video_id": "video3", "platform": "youtube", "frames": [{"frame_id": "f2", "ts": 20}, {"frame_id": "f3", "ts": 30}]},
        ]
        
        mock_video_processor.process_video = AsyncMock(side_effect=video_results)
        
        all_videos = [{"url": f"https://youtube.com/video{i}"} for i in range(3)]
        
        # Execute
        await service._process_and_emit_videos(all_videos, job_id, correlation_id)
        
        # Verify
        mock_event_emitter.publish_videos_keyframes_ready_batch.assert_called_once()
        call_args = mock_event_emitter.publish_videos_keyframes_ready_batch.call_args
        batch_payload = call_args[0][1]
        
        assert len(batch_payload) == 2
        assert all(len(video["frames"]) > 0 for video in batch_payload)

    @pytest.mark.asyncio
    async def test_batch_payload_preserves_video_data(
        self,
        service,
        mock_video_processor,
        mock_cleanup_service,
        mock_event_emitter
    ):
        """Test that batch payload preserves all video data."""
        # Setup
        service.video_processor = mock_video_processor
        service.cleanup_service = mock_cleanup_service
        service.event_emitter = mock_event_emitter
        
        job_id = str(uuid.uuid4())
        correlation_id = job_id
        
        # Videos with complete data
        video_results = [
            {
                "video_id": "video1",
                "platform": "youtube",
                "frames": [
                    {"frame_id": "f1", "ts": 10, "local_path": "/path/f1.jpg"},
                    {"frame_id": "f2", "ts": 20, "local_path": "/path/f2.jpg"}
                ],
                "created_new": True
            },
        ]
        
        mock_video_processor.process_video = AsyncMock(side_effect=video_results)
        
        all_videos = [{"url": "https://youtube.com/video1"}]
        
        # Execute
        await service._process_and_emit_videos(all_videos, job_id, correlation_id)
        
        # Verify
        call_args = mock_event_emitter.publish_videos_keyframes_ready_batch.call_args
        batch_payload = call_args[0][1]
        
        assert len(batch_payload) == 1
        video = batch_payload[0]
        assert video["video_id"] == "video1"
        assert video["platform"] == "youtube"
        assert len(video["frames"]) == 2
        assert video["frames"][0]["frame_id"] == "f1"
        assert video["frames"][0]["ts"] == 10
        assert video["frames"][0]["local_path"] == "/path/f1.jpg"

    @pytest.mark.asyncio
    async def test_no_event_emitter_no_crash(
        self,
        service,
        mock_video_processor,
        mock_cleanup_service
    ):
        """Test that processing works even without event emitter."""
        # Setup
        service.video_processor = mock_video_processor
        service.cleanup_service = mock_cleanup_service
        service.event_emitter = None  # No event emitter
        
        job_id = str(uuid.uuid4())
        correlation_id = job_id
        
        video_results = [
            {"video_id": "video1", "platform": "youtube", "frames": [{"frame_id": "f1", "ts": 10}]},
        ]
        
        mock_video_processor.process_video = AsyncMock(side_effect=video_results)
        
        all_videos = [{"url": "https://youtube.com/video1"}]
        
        # Execute - should not raise exception
        await service._process_and_emit_videos(all_videos, job_id, correlation_id)
        
        # Verify cleanup was still called
        mock_cleanup_service.run_auto_cleanup.assert_called_once_with(job_id)
