import pytest
from httpx import AsyncClient
from main import app
from common_py.crud.product_image_crud import ProductImageCRUD
from common_py.crud.video_frame_crud import VideoFrameCRUD
from common_py.crud.product_crud import ProductCRUD
from common_py.crud.video_crud import VideoCRUD
from services.job.job_service import JobService
from datetime import datetime, timezone
import pytz
from typing import Optional
from unittest.mock import AsyncMock, MagicMock
import api.features_endpoints # Import the features_endpoints module

# Mock instances (will be injected)
product_image_crud_mock = None
video_frame_crud_mock = None
product_crud_mock = None
video_crud_mock = None
job_service_mock = None

# Helper to convert datetime to GMT+7
def get_gmt7_time(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert datetime to GMT+7 timezone"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(pytz.timezone('Asia/Saigon'))

@pytest.fixture(autouse=True)
def setup_mocks(monkeypatch):
    global product_image_crud_mock, video_frame_crud_mock, product_crud_mock, video_crud_mock, job_service_mock
    product_image_crud_mock = AsyncMock(spec=ProductImageCRUD)
    video_frame_crud_mock = AsyncMock(spec=VideoFrameCRUD)
    product_crud_mock = AsyncMock(spec=ProductCRUD)
    video_crud_mock = AsyncMock(spec=VideoCRUD)
    job_service_mock = AsyncMock(spec=JobService)

    # Patch the global instances in the features_endpoints module
    monkeypatch.setattr("api.features_endpoints.product_image_crud_instance", product_image_crud_mock)
    monkeypatch.setattr("api.features_endpoints.video_frame_crud_instance", video_frame_crud_mock)
    monkeypatch.setattr("api.features_endpoints.product_crud_instance", product_crud_mock)
    monkeypatch.setattr("api.features_endpoints.video_crud_instance", video_crud_mock)
    monkeypatch.setattr("api.features_endpoints.job_service_instance", job_service_mock)
    monkeypatch.setattr("api.features_endpoints.db_instance", AsyncMock()) # Mock db_instance

# Test for GET /jobs/{job_id}/features/summary
@pytest.mark.asyncio
async def test_get_features_summary_success():
    job_id = "test_job_id"
    mock_updated_at = datetime.now(timezone.utc)

    job_service_mock.get_job = AsyncMock(return_value={"job_id": job_id, "updated_at": mock_updated_at})
    product_image_crud_mock.count_product_images_by_job = AsyncMock(side_effect=[10, 5, 3, 2])
    video_frame_crud_mock.count_video_frames_by_job = AsyncMock(side_effect=[20, 10, 6, 4])
    
    # Mock db_instance for updated_at
    api.features_endpoints.db_instance.fetch_one.return_value = {"updated_at": mock_updated_at} # Correctly mock db_instance

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/jobs/{job_id}/features/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["product_images"]["total"] == 10
    assert data["product_images"]["segment"]["done"] == 5
    assert data["product_images"]["embedding"]["done"] == 3
    assert data["product_images"]["keypoints"]["done"] == 2
    assert data["video_frames"]["total"] == 20
    assert data["video_frames"]["segment"]["done"] == 10
    assert data["video_frames"]["embedding"]["done"] == 6
    assert data["video_frames"]["keypoints"]["done"] == 4
    # Parse the response datetime and compare with the expected timezone-aware datetime
    response_updated_at = datetime.fromisoformat(data["updated_at"])
    expected_updated_at = get_gmt7_time(mock_updated_at)
    
    # Compare only year, month, day, hour, minute, second, and microsecond
    assert response_updated_at.replace(tzinfo=None) == expected_updated_at.replace(tzinfo=None)

@pytest.mark.asyncio
async def test_get_features_summary_job_not_found():
    job_id = "non_existent_job"
    job_service_mock.get_job = AsyncMock(return_value=None)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/jobs/{job_id}/features/summary")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Job {job_id} not found"}

# Test for GET /jobs/{job_id}/features/product-images
@pytest.mark.asyncio
async def test_get_job_product_images_features_success():
    job_id = "test_job_id"
    mock_image = MagicMock()
    mock_image.img_id = "img1"
    mock_image.product_id = "prod1"
    mock_image.masked_local_path = "/path/to/segment.png"
    mock_image.emb_rgb = b"some_embedding"
    mock_image.emb_gray = None
    mock_image.kp_blob_path = "/path/to/keypoints.json"
    mock_image.updated_at = datetime.now(timezone.utc)
    mock_image.created_at = datetime.now(timezone.utc)

    job_service_mock.get_job = AsyncMock(return_value={"job_id": job_id})
    product_image_crud_mock.list_product_images_by_job_with_features = AsyncMock(return_value=[mock_image])
    product_image_crud_mock.count_product_images_by_job = AsyncMock(return_value=1)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/jobs/{job_id}/features/product-images")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["img_id"] == "img1"
    assert item["has_segment"] is True
    assert item["has_embedding"] is True
    assert item["has_keypoints"] is True
    assert item["paths"]["segment"] == "/path/to/segment.png"
    assert item["paths"]["embedding"] is None
    assert item["paths"]["keypoints"] == "/path/to/keypoints.json"
    assert item["updated_at"] == get_gmt7_time(mock_image.updated_at).isoformat().replace("+07:00", "+07:00")

@pytest.mark.asyncio
async def test_get_job_product_images_features_job_not_found():
    job_id = "non_existent_job"
    job_service_mock.get_job = AsyncMock(return_value=None)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/jobs/{job_id}/features/product-images")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Job {job_id} not found"}

# Test for GET /jobs/{job_id}/features/video-frames
@pytest.mark.asyncio
async def test_get_job_video_frames_features_success():
    job_id = "test_job_id"
    mock_frame = MagicMock()
    mock_frame.frame_id = "frame1"
    mock_frame.video_id = "video1"
    mock_frame.ts = 1.23
    mock_frame.masked_local_path = "/path/to/frame_segment.png"
    mock_frame.emb_rgb = b"some_embedding"
    mock_frame.emb_gray = None
    mock_frame.kp_blob_path = "/path/to/frame_keypoints.json"
    mock_frame.updated_at = datetime.now(timezone.utc)
    mock_frame.created_at = datetime.now(timezone.utc)

    job_service_mock.get_job = AsyncMock(return_value={"job_id": job_id})
    video_frame_crud_mock.list_video_frames_by_job_with_features = AsyncMock(return_value=[mock_frame])
    video_frame_crud_mock.count_video_frames_by_job = AsyncMock(return_value=1)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/jobs/{job_id}/features/video-frames")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["frame_id"] == "frame1"
    assert item["ts"] == 1.23
    assert item["has_segment"] is True
    assert item["has_embedding"] is True
    assert item["has_keypoints"] is True
    assert item["paths"]["segment"] == "/path/to/frame_segment.png"
    assert item["paths"]["embedding"] is None
    assert item["paths"]["keypoints"] == "/path/to/frame_keypoints.json"
    assert item["updated_at"] == get_gmt7_time(mock_frame.updated_at).isoformat().replace("+07:00", "+07:00")

@pytest.mark.asyncio
async def test_get_job_video_frames_features_job_not_found():
    job_id = "non_existent_job"
    job_service_mock.get_job = AsyncMock(return_value=None)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/jobs/{job_id}/features/video-frames")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Job {job_id} not found"}

# Test for GET /features/product-images/{img_id}
@pytest.mark.asyncio
async def test_get_product_image_feature_success():
    img_id = "test_img_id"
    mock_image = MagicMock()
    mock_image.img_id = img_id
    mock_image.product_id = "prod1"
    mock_image.masked_local_path = "/path/to/segment.png"
    mock_image.emb_rgb = b"some_embedding"
    mock_image.emb_gray = None
    mock_image.kp_blob_path = "/path/to/keypoints.json"
    mock_image.updated_at = datetime.now(timezone.utc)
    mock_image.created_at = datetime.now(timezone.utc)

    product_image_crud_mock.get_product_image = AsyncMock(return_value=mock_image)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/features/product-images/{img_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["img_id"] == img_id
    assert data["product_id"] == "prod1"
    assert data["has_segment"] is True
    assert data["has_embedding"] is True
    assert data["has_keypoints"] is True
    assert data["paths"]["segment"] == "/path/to/segment.png"
    assert data["paths"]["embedding"] is None
    assert data["paths"]["keypoints"] == "/path/to/keypoints.json"
    assert data["updated_at"] == get_gmt7_time(mock_image.updated_at).isoformat().replace("+07:00", "+07:00")

@pytest.mark.asyncio
async def test_get_product_image_feature_not_found():
    img_id = "non_existent_img"
    product_image_crud_mock.get_product_image = AsyncMock(return_value=None)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/features/product-images/{img_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Product image {img_id} not found"}

# Test for GET /features/video-frames/{frame_id}
@pytest.mark.asyncio
async def test_get_video_frame_feature_success():
    frame_id = "test_frame_id"
    mock_frame = MagicMock()
    mock_frame.frame_id = frame_id
    mock_frame.video_id = "video1"
    mock_frame.ts = 1.23
    mock_frame.masked_local_path = "/path/to/frame_segment.png"
    mock_frame.emb_rgb = b"some_embedding"
    mock_frame.emb_gray = None
    mock_frame.kp_blob_path = "/path/to/frame_keypoints.json"
    mock_frame.updated_at = datetime.now(timezone.utc)
    mock_frame.created_at = datetime.now(timezone.utc)

    video_frame_crud_mock.get_video_frame = AsyncMock(return_value=mock_frame)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/features/video-frames/{frame_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["frame_id"] == frame_id
    assert data["video_id"] == "video1"
    assert data["ts"] == 1.23
    assert data["has_segment"] is True
    assert data["has_embedding"] is True
    assert data["has_keypoints"] is True
    assert data["paths"]["segment"] == "/path/to/frame_segment.png"
    assert data["paths"]["embedding"] is None
    assert data["paths"]["keypoints"] == "/path/to/frame_keypoints.json"
    assert data["updated_at"] == get_gmt7_time(mock_frame.updated_at).isoformat().replace("+07:00", "+07:00")

@pytest.mark.asyncio
async def test_get_video_frame_feature_not_found():
    frame_id = "non_existent_frame"
    video_frame_crud_mock.get_video_frame = AsyncMock(return_value=None)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/features/video-frames/{frame_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Video frame {frame_id} not found"}