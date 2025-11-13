"""Unit tests for VideoProcessor."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.video_processor import VideoProcessor
# Unused imports removed: VideoProcessingError, VideoDownloadError, DatabaseOperationError

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_db():
    """Mock database manager with proper pool handling."""
    db_mock = MagicMock()
    # Mock database connection and pool with all methods that might be called
    # Connection returns concrete dicts/lists to satisfy code paths expecting mappings

    async def _fetch_one_return(*args, **kwargs):
        # Return an example row as a dict when called in existence checks
        return {"video_id": str(uuid.uuid4())}

    async def _fetch_all_return(*args, **kwargs):
        return []

    async def _execute_return(*args, **kwargs):
        return None

    conn_mock = MagicMock(
        execute=AsyncMock(side_effect=_execute_return),
        fetchval=AsyncMock(return_value=1),
        fetch_one=AsyncMock(side_effect=_fetch_one_return),
        fetch_all=AsyncMock(side_effect=_fetch_all_return)
    )
    db_mock.pool = MagicMock()
    pool_mock = MagicMock(__aenter__=AsyncMock(return_value=conn_mock), __aexit__=AsyncMock())
    db_mock.pool.acquire = MagicMock(return_value=pool_mock)
    return db_mock


@pytest.fixture
def mock_event_emitter():
    """Mock event emitter."""
    emitter = MagicMock()
    emitter.publish_videos_keyframes_ready = AsyncMock()
    return emitter


@pytest.fixture
def mock_job_progress_manager():
    """Mock job progress manager."""
    manager = MagicMock()
    manager.update_job_progress = AsyncMock()
    return manager


@pytest.fixture
def video_processor(mock_db, mock_event_emitter, mock_job_progress_manager):
    """Create VideoProcessor instance with mocked dependencies."""
    vp = VideoProcessor(
        db=mock_db,
        event_emitter=mock_event_emitter,
        job_progress_manager=mock_job_progress_manager
    )
    # Ensure video_crud.get_video returns a visible object for FK visibility checks
    if getattr(vp, "video_crud", None) is not None:
        from unittest.mock import AsyncMock as _AsyncMock
        vp.video_crud.get_video = _AsyncMock(return_value=object())
    # Stub idempotency manager methods to avoid DB awaits
    from unittest.mock import AsyncMock as _AsyncMock
    vp.idempotency_manager._validate_database_connection = _AsyncMock(return_value=True)
    vp.idempotency_manager.get_existing_video = _AsyncMock(return_value=None)
    vp.idempotency_manager.create_video_with_idempotency = _AsyncMock(return_value=(True, str(uuid.uuid4())))

    async def _create_frame(video_id: str, frame_index: int, timestamp: float, local_path: str):
        return True, f"{video_id}_frame_{frame_index}"
    vp.idempotency_manager.create_frame_with_idempotency = _AsyncMock(side_effect=_create_frame)
    vp.idempotency_manager.get_existing_frames = _AsyncMock(return_value=[])
    return vp


class TestVideoProcessor:
    """Tests for VideoProcessor class."""

    def test_video_processor_initialization(self, mock_db, mock_event_emitter, mock_job_progress_manager):
        """Test VideoProcessor initialization."""
        processor = VideoProcessor(
            db=mock_db,
            event_emitter=mock_event_emitter,
            job_progress_manager=mock_job_progress_manager,
            video_dir_override="/test/path"
        )

        assert processor.db == mock_db
        assert processor.event_emitter == mock_event_emitter
        assert processor.job_progress_manager == mock_job_progress_manager
        assert processor._video_dir_override == "/test/path"
        assert processor.video_crud is not None
        assert processor.frame_crud is not None
        assert processor.keyframe_extractor is not None

    @pytest.mark.asyncio
    async def test_process_video_success(self, video_processor, mock_db):
        """Test successful video processing."""
        video_data = {
            "platform": "youtube",
            "url": "https://youtube.com/test",
            "title": "Test Video",
            "duration_s": 120
        }
        job_id = "test_job_123"

        # Mock database operations - ensure pool-based fetch_one returns no existing video
        # The conn_mock above returns a dict by default; override to None for existence check
        async def _no_existing(*args, **kwargs):
            return None
        # First existence check returns None, subsequent checks (e.g., parent video visible) return a row
        mock_db.pool.acquire.return_value.__aenter__.return_value.fetch_one = AsyncMock(side_effect=[None, {"video_id": "exists"}])

        # Mock keyframe extraction and frame CRUD entirely
        from unittest.mock import AsyncMock as _AsyncMock
        keyframes = [(10, "/path/frame1.jpg"), (20, "/path/frame2.jpg")]
        with patch.object(video_processor.keyframe_extractor, 'extract_keyframes', new=_AsyncMock(return_value=keyframes)):
            pass  # return_value handled by AsyncMock above

            # Mock frame CRUD entirely since it uses real db
            mock_frame_crud = MagicMock()
            mock_frame_crud.create_video_frame = AsyncMock()
            mock_frame_crud.fetch_all = AsyncMock(return_value=[])
            video_processor.frame_crud = mock_frame_crud

            result = await video_processor.process_video(video_data, job_id)

            assert result["platform"] == "youtube"
            assert result["video_id"] is not None
            assert len(result["frames"]) == 2
            assert result["frames"][0]["ts"] == 10
            assert result["frames"][0]["frame_id"].startswith(result["video_id"])

    @pytest.mark.asyncio
    async def test_process_video_tiktok_with_local_path(self, video_processor, mock_db):
        """Test TikTok video processing with existing local path."""
        video_data = {
            "platform": "tiktok",
            "url": "https://tiktok.com/test",
            "title": "Test TikTok",
            "local_path": "/local/path/video.mp4"
        }
        job_id = "test_job_123"

        # Mock database operations
        mock_db.pool.acquire.return_value.__aenter__.return_value.fetch_one = AsyncMock(return_value=None)  # No existing video

        result = await video_processor.process_video(video_data, job_id)

        assert result["platform"] == "tiktok"
        assert result["video_id"] is not None
        assert len(result["frames"]) == 0  # No keyframes extracted for pre-downloaded TikTok

    @pytest.mark.asyncio
    async def test_process_video_tiktok_download_success(self, video_processor, mock_db):
        """Test TikTok video processing with successful download."""
        video_data = {
            "platform": "tiktok",
            "url": "https://tiktok.com/test",
            "title": "Test TikTok"
        }
        job_id = "test_job_123"

        # Mock database operations
        mock_db.pool.acquire.return_value.__aenter__.return_value.fetch_one = AsyncMock(return_value=None)  # No existing video

        # Mock TikTok downloader
        with patch('services.video_processor.TikTokDownloader') as mock_downloader_class:
            mock_downloader = MagicMock()
            mock_downloader.orchestrate_download_and_extract = AsyncMock(return_value=True)
            mock_downloader_class.return_value = mock_downloader

            result = await video_processor.process_video(video_data, job_id)

            assert result["platform"] == "tiktok"
            assert result["video_id"] is not None
            assert len(result["frames"]) == 0  # Keyframes handled by downloader

    @pytest.mark.asyncio
    async def test_process_video_tiktok_download_failure(self, video_processor, mock_db):
        """Test TikTok video processing with failed download."""
        video_data = {
            "platform": "tiktok",
            "url": "https://tiktok.com/test",
            "title": "Test TikTok"
        }
        job_id = "test_job_123"

        # Mock database operations
        mock_db.pool.acquire.return_value.__aenter__.return_value.fetch_one = AsyncMock(return_value=None)  # No existing video

        # Mock TikTok downloader failure
        with patch('services.video_processor.TikTokDownloader') as mock_downloader_class:
            mock_downloader = MagicMock()
            mock_downloader.orchestrate_download_and_extract = AsyncMock(return_value=False)
            mock_downloader_class.return_value = mock_downloader

            result = await video_processor.process_video(video_data, job_id)

            assert result["platform"] == "tiktok"
            # The video record is created before the download attempt, so it has an ID
            assert result["video_id"] is not None
            assert len(result["frames"]) == 0

    @pytest.mark.asyncio
    async def test_process_video_exception_handling(self, video_processor, mock_db):
        """Test video processing exception handling."""
        video_data = {
            "platform": "youtube",
            "url": "https://youtube.com/test",
            "title": "Test Video"
        }
        job_id = "test_job_123"

        # Mock database to raise exception
        mock_db.fetch_one = AsyncMock(side_effect=Exception("Database error"))

        result = await video_processor.process_video(video_data, job_id)

        assert result["platform"] == "youtube"
        assert result["video_id"] is None
        assert len(result["frames"]) == 0

    @pytest.mark.asyncio
    async def test_create_and_save_video_record(self, video_processor, mock_db):
        """Test video record creation and saving."""
        video_data = {
            "platform": "youtube",
            "url": "https://youtube.com/test",
            "title": "Test Video",
            "duration_s": 120
        }
        job_id = "test_job_123"

        # Mock database operations for idempotency manager
        mock_db.pool.acquire.return_value.__aenter__.return_value.fetch_one = AsyncMock(return_value=None)  # No existing video
        mock_db.pool.acquire.return_value.__aenter__.return_value.fetch_one = AsyncMock(return_value=None)  # No existing video

        video, created_new = await video_processor._create_and_save_video_record(video_data, job_id)

        assert video.platform == "youtube"
        assert video.url == "https://youtube.com/test"
        assert video.title == "Test Video"
        assert video.duration_s == 120
        assert video.video_id is not None
        assert isinstance(created_new, bool)
        # With pool-based DB, execute is called on connection
        conn = mock_db.pool.acquire.return_value.__aenter__.return_value
        conn.execute.assert_called()

    @pytest.mark.asyncio
    async def test_save_keyframes(self, video_processor):
        """Test keyframe saving to database."""
        keyframes = [(10, "/path/frame1.jpg"), (20, "/path/frame2.jpg")]
        video_id = str(uuid.uuid4())

        # Mock database operations for idempotency manager
        _ = str(uuid.uuid4())
        video_processor.idempotency_manager.check_frame_exists = AsyncMock(return_value=False)
        video_processor.db.execute = AsyncMock()
        video_processor.db.fetch_one = AsyncMock(return_value=None)

        frame_data = await video_processor._save_keyframes(keyframes, video_id)

        assert len(frame_data) == 2
        assert frame_data[0]["ts"] == 10
        assert frame_data[0]["local_path"] == "/path/frame1.jpg"
        assert frame_data[0]["frame_id"] == f"{video_id}_frame_0"
        assert frame_data[1]["ts"] == 20
        assert frame_data[1]["frame_id"] == f"{video_id}_frame_1"

    @pytest.mark.asyncio
    async def test_emit_keyframes_ready_event_with_frames(self, video_processor, mock_event_emitter):
        """Test emitting keyframes ready event when frames exist."""
        from common_py.models import Video
        video = Video(video_id="test_id", platform="youtube", url="test", title="test")
        keyframes_data = [{"frame_id": "frame1", "ts": 10}]
        job_id = "test_job"

        await video_processor._emit_keyframes_ready_event(video, keyframes_data, job_id)

        mock_event_emitter.publish_videos_keyframes_ready.assert_called_once_with(
            "test_id", keyframes_data, job_id
        )

    @pytest.mark.asyncio
    async def test_emit_keyframes_ready_event_no_frames(self, video_processor, mock_event_emitter):
        """Test emitting keyframes ready event when no frames exist."""
        from common_py.models import Video
        video = Video(video_id="test_id", platform="youtube", url="test", title="test")
        keyframes_data = []
        job_id = "test_job"

        await video_processor._emit_keyframes_ready_event(video, keyframes_data, job_id)

        mock_event_emitter.publish_videos_keyframes_ready.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_progress_with_manager(self, video_processor, mock_job_progress_manager):
        """Test updating job progress when manager is available."""
        job_id = "test_job"

        await video_processor._update_progress(job_id)

        mock_job_progress_manager.update_job_progress.assert_called_once_with(
            job_id, "video", 0, 1, "crawling"
        )

    @pytest.mark.asyncio
    async def test_update_progress_without_manager(self, video_processor):
        """Test updating job progress when manager is not available."""
        video_processor.job_progress_manager = None
        job_id = "test_job"

        # Should not raise exception
        await video_processor._update_progress(job_id)

    def test_initialize_keyframe_extractor(self, video_processor, tmp_path):
        """Test keyframe extractor initialization."""
        # This should not raise exception
        test_dir = tmp_path / "keyframes"
        video_processor.initialize_keyframe_extractor(str(test_dir))

        # Verify the extractor was reinitialized
        assert video_processor.keyframe_extractor is not None
