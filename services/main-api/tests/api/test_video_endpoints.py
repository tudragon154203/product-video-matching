import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import json
import pytz
from httpx import AsyncClient
from main import app

# Import dependencies that will be mocked
from services.job.job_service import JobService
from services.job.job_management_service import JobManagementService
from common_py.crud.video_crud import VideoCRUD
from common_py.crud.video_frame_crud import VideoFrameCRUD
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from handlers.database_handler import DatabaseHandler
import os

# Mock data
MOCK_JOB_ID = "job123"
MOCK_VIDEO_ID_1 = "video1"
MOCK_VIDEO_ID_2 = "video2"
MOCK_FRAME_ID_1 = "frame1"
MOCK_FRAME_ID_2 = "frame2"

# Mock Video and VideoFrame models
class MockVideo:
    def __init__(self, video_id, platform, url, title, duration_s, created_at, updated_at=None, job_id=MOCK_JOB_ID):
        self.video_id = video_id
        self.platform = platform
        self.url = url
        self.title = title
        self.duration_s = duration_s
        self.created_at = created_at
        self.updated_at = updated_at if updated_at else created_at
        self.job_id = job_id

class MockVideoFrame:
    def __init__(self, frame_id, video_id, ts, local_path, created_at, updated_at=None):
        self.frame_id = frame_id
        self.video_id = video_id
        self.ts = ts
        self.local_path = local_path
        self.created_at = created_at
        self.updated_at = updated_at if updated_at else created_at

# Helper to convert datetime to GMT+7
def to_gmt7(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(pytz.timezone('Asia/Saigon'))

# Global mock instances
job_service_mock: JobService
job_management_service_mock: JobManagementService
video_crud_mock: VideoCRUD
video_frame_crud_mock: VideoFrameCRUD
db_mock: DatabaseManager
broker_mock: MessageBroker

@pytest.fixture(autouse=True)
def setup_mocks(monkeypatch):
    global job_service_mock, job_management_service_mock, video_crud_mock, video_frame_crud_mock, db_mock, broker_mock
    
    # Set environment variables
    monkeypatch.setenv("POSTGRES_DSN", "postgresql://user:password@host:port/database")
    monkeypatch.setenv("BUS_BROKER", "amqp://guest:guest@localhost:5672/")

    # Initialize mocks
    job_service_mock = AsyncMock(spec=JobService)
    job_management_service_mock = AsyncMock(spec=JobManagementService)
    
    video_crud_mock = MagicMock()
    video_crud_mock.create_video = AsyncMock(return_value="new_video_id")
    video_crud_mock.get_video = AsyncMock(return_value=None)
    video_crud_mock.list_videos = AsyncMock(return_value=[])
    video_crud_mock.list_videos_by_job = AsyncMock(return_value=[])
    video_crud_mock.count_videos_by_job = AsyncMock(return_value=0)

    video_frame_crud_mock = MagicMock()
    video_frame_crud_mock.create_video_frame = AsyncMock(return_value="new_frame_id")
    video_frame_crud_mock.update_embeddings = AsyncMock()
    video_frame_crud_mock.get_video_frame = AsyncMock(return_value=None)
    video_frame_crud_mock.list_video_frames = AsyncMock(return_value=[])
    video_frame_crud_mock.list_video_frames_by_video = AsyncMock(return_value=[])
    video_frame_crud_mock.count_video_frames_by_video = AsyncMock(return_value=0)
    video_frame_crud_mock.count_video_frames_by_job = AsyncMock(return_value=0)
    video_frame_crud_mock.list_video_frames_by_job_with_features = AsyncMock(return_value=[])
    video_frame_crud_mock.get_video_frames_count = AsyncMock(return_value=0)

    db_mock = AsyncMock(spec=DatabaseManager)
    broker_mock = AsyncMock(spec=MessageBroker)

    # Set job_service_mock's job_management_service attribute
    job_service_mock.job_management_service = job_management_service_mock

    # Import dependency functions from the endpoint modules
    from api.video_endpoints import get_db, get_broker, get_job_service, get_video_crud, get_video_frame_crud
    
    # Override dependencies in FastAPI app by replacing the dependency functions
    app.dependency_overrides[get_db] = lambda: db_mock
    app.dependency_overrides[get_broker] = lambda: broker_mock
    app.dependency_overrides[get_job_service] = lambda: job_service_mock
    app.dependency_overrides[get_video_crud] = lambda: video_crud_mock
    app.dependency_overrides[get_video_frame_crud] = lambda: video_frame_crud_mock

    # Configure mock job service and job management service
    # Create mock job status return value
    from models.schemas import JobStatusResponse
    mock_job_status = JobStatusResponse(
        job_id=MOCK_JOB_ID,
        phase="completed",
        percent=100.0,
        counts={"products": 0, "videos": 0, "images": 0, "frames": 0},
        updated_at=datetime.now(timezone.utc)
    )
    job_service_mock.get_job_status = AsyncMock(return_value=mock_job_status)
    job_management_service_mock.get_job_status = AsyncMock(return_value=mock_job_status)
    
    # Configure mock video CRUD
    video_crud_mock.list_videos_by_job.return_value = [
        MockVideo(MOCK_VIDEO_ID_1, "youtube", "url1", "Video Title 1", 120, datetime.now(timezone.utc) - timedelta(days=5)),
        MockVideo(MOCK_VIDEO_ID_2, "bilibili", "url2", "Another Video", 240, datetime.now(timezone.utc) - timedelta(days=10))
    ]
    video_crud_mock.count_videos_by_job.return_value = 2
    video_crud_mock.get_video.side_effect = lambda video_id: {
        MOCK_VIDEO_ID_1: MockVideo(MOCK_VIDEO_ID_1, "youtube", "url1", "Video Title 1", 120, datetime.now(timezone.utc) - timedelta(days=5)),
        MOCK_VIDEO_ID_2: MockVideo(MOCK_VIDEO_ID_2, "bilibili", "url2", "Another Video", 240, datetime.now(timezone.utc) - timedelta(days=10))
    }.get(video_id)
    video_frame_crud_mock.get_video_frames_count = AsyncMock(return_value=50)
    
    # Configure mock video frame CRUD
    video_frame_crud_mock.list_video_frames_by_video.return_value = [
        MockVideoFrame(MOCK_FRAME_ID_1, MOCK_VIDEO_ID_1, 10.5, "/path/to/frame1.jpg", datetime.now(timezone.utc) - timedelta(days=1)),
        MockVideoFrame(MOCK_FRAME_ID_2, MOCK_VIDEO_ID_1, 20.0, "/path/to/frame2.jpg", datetime.now(timezone.utc) - timedelta(days=2))
    ]
    video_frame_crud_mock.count_video_frames_by_video.return_value = 2
    
    yield
    
    # Clear overrides after the test
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_job_videos_success():
    """Test GET /jobs/{job_id}/videos with success."""
    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
        response = await ac.get(f"/jobs/{MOCK_JOB_ID}/videos")
    
    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["video_id"] == MOCK_VIDEO_ID_1
    assert "updated_at" in data["items"][0]
    assert data["items"][0]["updated_at"].endswith("+07:00")
    print("✓ test_get_job_videos_success passed")

@pytest.mark.asyncio
async def test_get_job_videos_not_found():
    """Test GET /jobs/{job_id}/videos for job not found."""
    from models.schemas import JobStatusResponse
    mock_job_status = JobStatusResponse(
        job_id="nonexistent_job",
        phase="unknown",
        percent=0.0,
        counts={"products": 0, "videos": 0, "images": 0, "frames": 0},
        updated_at=None
    )
    job_service_mock.get_job_status.return_value = mock_job_status
    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
        response = await ac.get(f"/jobs/nonexistent_job/videos")
    
    if response.status_code != 404:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 404
    assert "Job nonexistent_job not found" in response.json()["detail"]
    print("✓ test_get_job_videos_not_found passed")

@pytest.mark.asyncio
async def test_get_job_videos_with_query_params():
    """Test GET /jobs/{job_id}/videos with query parameters."""
    video_crud_mock.list_videos_by_job.return_value = [
        MockVideo(MOCK_VIDEO_ID_1, "youtube", "url1", "Specific Video Title", 120, datetime.now())
    ]
    video_crud_mock.count_videos_by_job.return_value = 1
    
    params = {
        "q": "Specific",
        "platform": "youtube",
        "min_frames": 10,
        "limit": 1,
        "offset": 0,
        "sort_by": "title",
        "order": "ASC"
    }
    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
        response = await ac.get(f"/jobs/{MOCK_JOB_ID}/videos", params=params)
    
    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Specific Video Title"
    print("✓ test_get_job_videos_with_query_params passed")

@pytest.mark.asyncio
async def test_get_video_frames_success():
    """Test GET /jobs/{job_id}/videos/{video_id}/frames with success."""
    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
        response = await ac.get(f"/jobs/{MOCK_JOB_ID}/videos/{MOCK_VIDEO_ID_1}/frames")
    
    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["frame_id"] == MOCK_FRAME_ID_1
    assert "updated_at" in data["items"][0]
    assert data["items"][0]["updated_at"].endswith("+07:00")
    print("✓ test_get_video_frames_success passed")

@pytest.mark.asyncio
async def test_get_job_videos_includes_new_fields():
    """Test that GET /jobs/{job_id}/videos includes thumbnail_url and preview_frame fields."""
    # Mock video with frames for preview_frame selection
    mock_video = MockVideo(MOCK_VIDEO_ID_1, "youtube", "url1", "Video Title 1", 120, datetime.now(timezone.utc) - timedelta(days=5))

    # Mock frames for preview frame selection
    mock_frames = [
        MockVideoFrame("frame-middle", MOCK_VIDEO_ID_1, 60.0, "/app/data/videos/frames/frame-middle.jpg",
                      datetime.now(timezone.utc), datetime.now(timezone.utc)),
        MockVideoFrame("frame-early", MOCK_VIDEO_ID_1, 10.0, "/app/data/videos/frames/frame-early.jpg",
                      datetime.now(timezone.utc), datetime.now(timezone.utc))
    ]

    video_crud_mock.list_videos_by_job.return_value = [mock_video]
    video_crud_mock.count_videos_by_job.return_value = 1
    video_frame_crud_mock.get_video_frames_count = AsyncMock(return_value=2)
    video_frame_crud_mock.list_video_frames_by_video = AsyncMock(return_value=mock_frames)

    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
        response = await ac.get(f"/jobs/{MOCK_JOB_ID}/videos")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1

    video_item = data["items"][0]
    # Check that new field is present
    assert "preview_frame" in video_item

    # Check preview_frame structure
    preview_frame = video_item["preview_frame"]
    assert preview_frame is not None
    assert "frame_id" in preview_frame
    assert "ts" in preview_frame
    assert "url" in preview_frame
    assert "segment_url" in preview_frame

    # Should select frame closest to middle (60.0 for 120s video)
    assert preview_frame["frame_id"] == "frame-middle"
    assert preview_frame["ts"] == 60.0
    assert preview_frame["url"] == "/files/videos/frames/frame-middle.jpg"
    assert preview_frame["segment_url"] is None  # No segment path in mock

    print("✓ test_get_job_videos_includes_new_fields passed")

@pytest.mark.asyncio
async def test_get_job_videos_no_frames():
    """Test that GET /jobs/{job_id}/videos handles videos with no frames."""
    mock_video = MockVideo(MOCK_VIDEO_ID_1, "youtube", "url1", "Video Title 1", 120, datetime.now(timezone.utc))

    video_crud_mock.list_videos_by_job.return_value = [mock_video]
    video_crud_mock.count_videos_by_job.return_value = 1
    video_frame_crud_mock.get_video_frames_count = AsyncMock(return_value=0)
    video_frame_crud_mock.list_video_frames_by_video = AsyncMock(return_value=[])

    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
        response = await ac.get(f"/jobs/{MOCK_JOB_ID}/videos")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1

    video_item = data["items"][0]
    # Check that new field is present but null/None when no frames
    assert "preview_frame" in video_item
    assert video_item["preview_frame"] is None

    print("✓ test_get_job_videos_no_frames passed")

# ... rest of the test cases ...