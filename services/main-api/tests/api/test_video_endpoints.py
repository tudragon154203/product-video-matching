import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta, timezone
import json
import pytz
from fastapi.testclient import TestClient
import sys

# Add the current directory to sys.path to ensure 'main' module is found
sys.path.insert(0, ".")

# Import the main FastAPI app from the service
import main

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

@pytest.fixture
def client():
    """Fixture to create a TestClient for the FastAPI app."""
    return TestClient(main.app)

@pytest.fixture
def mock_db_instances():
    """Fixture to mock global database and CRUD instances."""
    with patch('api.video_endpoints.job_service_instance', new_callable=AsyncMock) as mock_job_service, \
         patch('api.video_endpoints.video_crud_instance', new_callable=AsyncMock) as mock_video_crud, \
         patch('api.video_endpoints.video_frame_crud_instance', new_callable=AsyncMock) as mock_video_frame_crud:
        
        # Configure mock job service
        mock_job_service.get_job.return_value = {"job_id": MOCK_JOB_ID} # Job exists
        
        # Configure mock video CRUD
        mock_video_crud.list_videos_by_job.return_value = [
            MockVideo(MOCK_VIDEO_ID_1, "youtube", "url1", "Video Title 1", 120, datetime.now() - timedelta(days=5)),
            MockVideo(MOCK_VIDEO_ID_2, "bilibili", "url2", "Another Video", 240, datetime.now() - timedelta(days=10))
        ]
        mock_video_crud.count_videos_by_job.return_value = 2
        mock_video_crud.get_video.side_effect = lambda video_id: {
            MOCK_VIDEO_ID_1: MockVideo(MOCK_VIDEO_ID_1, "youtube", "url1", "Video Title 1", 120, datetime.now() - timedelta(days=5)),
            MOCK_VIDEO_ID_2: MockVideo(MOCK_VIDEO_ID_2, "bilibili", "url2", "Another Video", 240, datetime.now() - timedelta(days=10))
        }.get(video_id)
        mock_video_crud.get_video_frames_count.return_value = 50 # Example frame count
        
        # Configure mock video frame CRUD
        mock_video_frame_crud.list_video_frames_by_video.return_value = [
            MockVideoFrame(MOCK_FRAME_ID_1, MOCK_VIDEO_ID_1, 10.5, "/path/to/frame1.jpg", datetime.now() - timedelta(days=1)),
            MockVideoFrame(MOCK_FRAME_ID_2, MOCK_VIDEO_ID_1, 20.0, "/path/to/frame2.jpg", datetime.now() - timedelta(days=2))
        ]
        mock_video_frame_crud.count_video_frames_by_video.return_value = 2
        
        yield mock_job_service, mock_video_crud, mock_video_frame_crud

def test_get_job_videos_success(client, mock_db_instances):
    """Test GET /jobs/{job_id}/videos with success."""
    response = client.get(f"/jobs/{MOCK_JOB_ID}/videos")
    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["video_id"] == MOCK_VIDEO_ID_1
    assert "updated_at" in data["items"][0]
    # Check if updated_at is in GMT+7 (Asia/Saigon)
    assert data["items"][0]["updated_at"].endswith("+07:00")
    print("✓ test_get_job_videos_success passed")

def test_get_job_videos_not_found(client, mock_db_instances):
    """Test GET /jobs/{job_id}/videos for job not found."""
    mock_db_instances[0].get_job.return_value = None # Mock job_service_instance.get_job
    response = client.get(f"/jobs/nonexistent_job/videos")
    if response.status_code != 404:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 404
    assert "Job nonexistent_job not found" in response.json()["detail"]
    print("✓ test_get_job_videos_not_found passed")

def test_get_job_videos_with_query_params(client, mock_db_instances):
    """Test GET /jobs/{job_id}/videos with query parameters."""
    mock_db_instances[1].list_videos_by_job.return_value = [
        MockVideo(MOCK_VIDEO_ID_1, "youtube", "url1", "Specific Video Title", 120, datetime.now())
    ]
    mock_db_instances[1].count_videos_by_job.return_value = 1
    
    params = {
        "q": "Specific",
        "platform": "youtube",
        "min_frames": 10,
        "limit": 1,
        "offset": 0,
        "sort_by": "title",
        "order": "ASC" # Changed from "asc" to "ASC"
    }
    response = client.get(f"/jobs/{MOCK_JOB_ID}/videos", params=params)
    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Specific Video Title"
    print("✓ test_get_job_videos_with_query_params passed")

def test_get_video_frames_success(client, mock_db_instances):
    """Test GET /jobs/{job_id}/videos/{video_id}/frames with success."""
    response = client.get(f"/jobs/{MOCK_JOB_ID}/videos/{MOCK_VIDEO_ID_1}/frames")
    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["frame_id"] == MOCK_FRAME_ID_1
    assert "updated_at" in data["items"][0]
    # Check if updated_at is in GMT+7 (Asia/Saigon)
    assert data["items"][0]["updated_at"].endswith("+07:00")
    print("✓ test_get_video_frames_success passed")

def test_get_video_frames_job_not_found(client, mock_db_instances):
    """Test GET /jobs/{job_id}/videos/{video_id}/frames for job not found."""
    mock_db_instances[0].get_job.return_value = None
    response = client.get(f"/jobs/nonexistent_job/videos/{MOCK_VIDEO_ID_1}/frames")
    if response.status_code != 404:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 404
    assert "Job nonexistent_job not found" in response.json()["detail"]
    print("✓ test_get_video_frames_job_not_found passed")

def test_get_video_frames_video_not_found(client, mock_db_instances):
    """Test GET /jobs/{job_id}/videos/{video_id}/frames for video not found."""
    mock_db_instances[1].get_video.return_value = None
    response = client.get(f"/jobs/{MOCK_JOB_ID}/videos/nonexistent_video/frames")
    if response.status_code != 404:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 404
    assert "Video nonexistent_video not found" in response.json()["detail"]
    print("✓ test_get_video_frames_video_not_found passed")

def test_get_video_frames_video_not_belong_to_job(client, mock_db_instances):
    """Test GET /jobs/{job_id}/videos/{video_id}/frames when video does not belong to job."""
    mock_db_instances[1].get_video.side_effect = lambda video_id: MockVideo(MOCK_VIDEO_ID_1, "youtube", "url1", "Title", 100, datetime.now(), job_id="another_job")
    response = client.get(f"/jobs/{MOCK_JOB_ID}/videos/{MOCK_VIDEO_ID_1}/frames")
    if response.status_code != 404:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 404
    assert f"Video {MOCK_VIDEO_ID_1} does not belong to job {MOCK_JOB_ID}" in response.json()["detail"]
    print("✓ test_get_video_frames_video_not_belong_to_job passed")

def test_get_video_frames_with_query_params(client, mock_db_instances):
    """Test GET /jobs/{job_id}/videos/{video_id}/frames with query parameters."""
    mock_db_instances[2].list_video_frames_by_video.return_value = [
        MockVideoFrame(MOCK_FRAME_ID_1, MOCK_VIDEO_ID_1, 5.0, "/path/to/frame_sorted.jpg", datetime.now())
    ]
    mock_db_instances[2].count_video_frames_by_video.return_value = 1
    
    params = {
        "limit": 1,
        "offset": 0,
        "sort_by": "ts",
        "order": "ASC" # Changed from "asc" to "ASC"
    }
    response = client.get(f"/jobs/{MOCK_JOB_ID}/videos/{MOCK_VIDEO_ID_1}/frames", params=params)
    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["ts"] == 5.0
    print("✓ test_get_video_frames_with_query_params passed")
