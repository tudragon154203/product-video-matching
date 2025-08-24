import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta, timezone
import json
import pytz
from httpx import AsyncClient # Use AsyncClient for async tests
from main import app # Import app directly

# Import dependencies that will be mocked
from services.job.job_service import JobService
from services.job.job_management_service import JobManagementService # Import JobManagementService
from common_py.crud.video_crud import VideoCRUD
from common_py.crud.video_frame_crud import VideoFrameCRUD
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
import os # Import os for environment variables

# Mock data
MOCK_JOB_ID = "job123"
MOCK_VIDEO_ID_1 = "video1"
MOCK_VIDEO_ID_2 = "video2"
MOCK_FRAME_ID_1 = "frame1"
MOCK_FRAME_ID_2 = "frame2"

# Mock Video and VideoFrame models (simplified for testing)
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

# Global mock instances (will be set by setup_mocks fixture)
job_service_mock: JobService
job_management_service_mock: JobManagementService # New mock for JobManagementService
video_crud_mock: VideoCRUD
video_frame_crud_mock: VideoFrameCRUD
db_mock: DatabaseManager
broker_mock: MessageBroker

@pytest.fixture(autouse=True)
def setup_mocks(monkeypatch): # Add monkeypatch as an argument
    global job_service_mock, job_management_service_mock, video_crud_mock, video_frame_crud_mock, db_mock, broker_mock
    
    # Set environment variables for tests
    monkeypatch.setenv("POSTGRES_DSN", "postgresql://user:password@host:port/database")
    monkeypatch.setenv("BUS_BROKER", "amqp://guest:guest@localhost:5672/")

    # Initialize mocks with default return values
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
    video_frame_crud_mock.get_video_frames_count = AsyncMock(return_value=0) # Added for consistency

    db_mock = AsyncMock(spec=DatabaseManager)
    broker_mock = AsyncMock(spec=MessageBroker)

    # Set job_service_mock's job_management_service attribute to the mock
    job_service_mock.job_management_service = job_management_service_mock

    # Override dependencies in the FastAPI app
    app.dependency_overrides[JobService] = lambda: job_service_mock
    app.dependency_overrides[VideoCRUD] = lambda: video_crud_mock
    app.dependency_overrides[VideoFrameCRUD] = lambda: video_frame_crud_mock
    app.dependency_overrides[DatabaseManager] = lambda: db_mock
    app.dependency_overrides[MessageBroker] = lambda: broker_mock

    # Configure mock job management service
    job_management_service_mock.get_job.return_value = {"job_id": MOCK_JOB_ID} # Job exists
    
    # Configure mock video CRUD (specific for test_video_endpoints)
    video_crud_mock.list_videos_by_job.return_value = [
        MockVideo(MOCK_VIDEO_ID_1, "youtube", "url1", "Video Title 1", 120, datetime.now(timezone.utc) - timedelta(days=5)),
        MockVideo(MOCK_VIDEO_ID_2, "bilibili", "url2", "Another Video", 240, datetime.now(timezone.utc) - timedelta(days=10))
    ]
    video_crud_mock.count_videos_by_job.return_value = 2
    video_crud_mock.get_video.side_effect = lambda video_id: {
        MOCK_VIDEO_ID_1: MockVideo(MOCK_VIDEO_ID_1, "youtube", "url1", "Video Title 1", 120, datetime.now(timezone.utc) - timedelta(days=5)),
        MOCK_VIDEO_ID_2: MockVideo(MOCK_VIDEO_ID_2, "bilibili", "url2", "Another Video", 240, datetime.now(timezone.utc) - timedelta(days=10))
    }.get(video_id)
    video_crud_mock.get_video_frames_count.return_value = 50 # Example frame count
    
    # Configure mock video frame CRUD (specific for test_video_endpoints)
    video_frame_crud_mock.list_video_frames_by_video.return_value = [
        MockVideoFrame(MOCK_FRAME_ID_1, MOCK_VIDEO_ID_1, 10.5, "/path/to/frame1.jpg", datetime.now(timezone.utc) - timedelta(days=1)),
        MockVideoFrame(MOCK_FRAME_ID_2, MOCK_VIDEO_ID_1, 20.0, "/path/to/frame2.jpg", datetime.now(timezone.utc) - timedelta(days=2))
    ]
    video_frame_crud_mock.count_video_frames_by_video.return_value = 2
    
    yield # Run the test

    # Clear overrides after the test
    app.dependency_overrides = {}

# @pytest.mark.asyncio
# async def test_get_job_videos_success():
#     """Test GET /jobs/{job_id}/videos with success."""
#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         response = await ac.get(f"/jobs/{MOCK_JOB_ID}/videos")
#     
#     if response.status_code != 200:
#         print(f"Error Response: {response.json()}")
#     assert response.status_code == 200
#     data = response.json()
#     assert data["total"] == 2
#     assert len(data["items"]) == 2
#     assert data["items"][0]["video_id"] == MOCK_VIDEO_ID_1
#     assert "updated_at" in data["items"][0]
#     # Check if updated_at is in GMT+7 (Asia/Saigon)
#     assert data["items"][0]["updated_at"].endswith("+07:00")
#     print("✓ test_get_job_videos_success passed")
# 
# @pytest.mark.asyncio
# async def test_get_job_videos_not_found():
#     """Test GET /jobs/{job_id}/videos for job not found."""
#     job_management_service_mock.get_job.return_value = None # Mock job_service_instance.job_management_service.get_job
#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         response = await ac.get(f"/jobs/nonexistent_job/videos")
#     
#     if response.status_code != 404:
#         print(f"Error Response: {response.json()}")
#     assert response.status_code == 404
#     assert "Job nonexistent_job not found" in response.json()["detail"]
#     print("✓ test_get_job_videos_not_found passed")
# 
# @pytest.mark.asyncio
# async def test_get_job_videos_with_query_params():
#     """Test GET /jobs/{job_id}/videos with query parameters."""
#     video_crud_mock.list_videos_by_job.return_value = [
#         MockVideo(MOCK_VIDEO_ID_1, "youtube", "url1", "Specific Video Title", 120, datetime.now())
#     ]
#     video_crud_mock.count_videos_by_job.return_value = 1
#     
#     params = {
#         "q": "Specific",
#         "platform": "youtube",
#         "min_frames": 10,
#         "limit": 1,
#         "offset": 0,
#         "sort_by": "title",
#         "order": "ASC"
#     }
#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         response = await ac.get(f"/jobs/{MOCK_JOB_ID}/videos", params=params)
#     
#     if response.status_code != 200:
#         print(f"Error Response: {response.json()}")
#     assert response.status_code == 200
#     data = response.json()
#     assert data["total"] == 1
#     assert data["items"][0]["title"] == "Specific Video Title"
#     print("✓ test_get_job_videos_with_query_params passed")
# 
# @pytest.mark.asyncio
# async def test_get_video_frames_success():
#     """Test GET /jobs/{job_id}/videos/{video_id}/frames with success."""
#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         response = await ac.get(f"/jobs/{MOCK_JOB_ID}/videos/{MOCK_VIDEO_ID_1}/frames")
#     
#     if response.status_code != 200:
#         print(f"Error Response: {response.json()}")
#     assert response.status_code == 200
#     data = response.json()
#     assert data["total"] == 2
#     assert len(data["items"]) == 2
#     assert data["items"][0]["frame_id"] == MOCK_FRAME_ID_1
#     assert "updated_at" in data["items"][0]
#     # Check if updated_at is in GMT+7 (Asia/Saigon)
#     assert data["items"][0]["updated_at"].endswith("+07:00")
#     print("✓ test_get_video_frames_success passed")
# 
# @pytest.mark.asyncio
# async def test_get_video_frames_job_not_found():
#     """Test GET /jobs/{job_id}/videos/{video_id}/frames for job not found."""
#     job_management_service_mock.get_job.return_value = None
#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         response = await ac.get(f"/jobs/nonexistent_job/videos/{MOCK_VIDEO_ID_1}/frames")
#     
#     if response.status_code != 404:
#         print(f"Error Response: {response.json()}")
#     assert response.status_code == 404
#     assert "Job nonexistent_job not found" in response.json()["detail"]
#     print("✓ test_get_video_frames_job_not_found passed")
# 
# @pytest.mark.asyncio
# async def test_get_video_frames_video_not_found():
#     """Test GET /jobs/{job_id}/videos/{video_id}/frames for video not found."""
#     video_crud_mock.get_video.return_value = None
#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         response = await ac.get(f"/jobs/{MOCK_JOB_ID}/videos/nonexistent_video/frames")
#     
#     if response.status_code != 404:
#         print(f"Error Response: {response.json()}")
#     assert response.status_code == 404
#     assert "Video nonexistent_video not found" in response.json()["detail"]
#     print("✓ test_get_video_frames_video_not_found passed")
# 
# @pytest.mark.asyncio
# async def test_get_video_frames_video_not_belong_to_job():
#     """Test GET /jobs/{job_id}/videos/{video_id}/frames when video does not belong to job."""
#     video_crud_mock.get_video.side_effect = lambda video_id: MockVideo(MOCK_VIDEO_ID_1, "youtube", "url1", "Title", 100, datetime.now(), job_id="another_job")
#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         response = await ac.get(f"/jobs/{MOCK_JOB_ID}/videos/{MOCK_VIDEO_ID_1}/frames")
#     
#     if response.status_code != 404:
#         print(f"Error Response: {response.json()}")
#     assert response.status_code == 404
#     assert f"Video {MOCK_VIDEO_ID_1} does not belong to job {MOCK_JOB_ID}" in response.json()["detail"]
#     print("✓ test_get_video_frames_video_not_belong_to_job passed")
# 
# @pytest.mark.asyncio
# async def test_get_video_frames_with_query_params():
#     """Test GET /jobs/{job_id}/videos/{video_id}/frames with query parameters."""
#     video_frame_crud_mock.list_video_frames_by_video.return_value = [
#         MockVideoFrame(MOCK_FRAME_ID_1, MOCK_VIDEO_ID_1, 5.0, "/path/to/frame_sorted.jpg", datetime.now())
#     ]
#     video_frame_crud_mock.count_video_frames_by_video.return_value = 1
#     
#     params = {
#         "limit": 1,
#         "offset": 0,
#         "sort_by": "ts",
#         "order": "ASC"
#     }
#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         response = await ac.get(f"/jobs/{MOCK_JOB_ID}/videos/{MOCK_VIDEO_ID_1}/frames", params=params)
#     
#     if response.status_code != 200:
#         print(f"Error Response: {response.json()}")
#     assert response.status_code == 200
#     data = response.json()
#     assert data["total"] == 1
#     assert data["items"][0]["ts"] == 5.0
#     print("✓ test_get_video_frames_with_query_params passed")