from unittest.mock import AsyncMock, MagicMock
from typing import Optional
import pytz
from datetime import datetime, timezone
from common_py.messaging import MessageBroker  # Import MessageBroker
from common_py.database import DatabaseManager  # Import DatabaseManager
# Import JobManagementService
from services.job.job_management_service import JobManagementService
from services.job.job_service import JobService
from common_py.crud.video_crud import VideoCRUD
from common_py.crud.product_crud import ProductCRUD
from common_py.crud.video_frame_crud import VideoFrameCRUD
from common_py.crud.product_image_crud import ProductImageCRUD
from main import app
from httpx import AsyncClient
import pytest
pytestmark = pytest.mark.integration

# Mock instances (will be set by setup_mocks fixture)
product_image_crud_mock: ProductImageCRUD  # noqa: F821
video_frame_crud_mock: VideoFrameCRUD  # noqa: F821
product_crud_mock: ProductCRUD  # noqa: F821
video_crud_mock: VideoCRUD  # noqa: F821
job_service_mock: JobService  # noqa: F821
# New mock for JobManagementService
job_management_service_mock: JobManagementService  # noqa: F821
db_mock: DatabaseManager  # noqa: F821
broker_mock: MessageBroker  # noqa: F821

# Helper to convert datetime to GMT+7


def get_gmt7_time(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert datetime to GMT+7 timezone"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(pytz.timezone('Asia/Saigon'))


@pytest.fixture(autouse=True)
def setup_mocks(monkeypatch):  # Add monkeypatch as an argument
    global product_image_crud_mock, video_frame_crud_mock, product_crud_mock, \
        video_crud_mock, job_service_mock, job_management_service_mock, \
        db_mock, broker_mock

    # Set environment variables for tests
    monkeypatch.setenv(
        "POSTGRES_DSN", "postgresql://user:password@host:port/database")
    monkeypatch.setenv("BUS_BROKER", "amqp://guest:guest@localhost:5672/")

    # Initialize mocks
    # Initialize mocks with default return values
    # Initialize mocks
    product_image_crud_mock = MagicMock()
    product_image_crud_mock.create_product_image = AsyncMock(
        return_value="new_img_id")
    product_image_crud_mock.update_embeddings = AsyncMock()
    product_image_crud_mock.get_product_image = AsyncMock(return_value=None)
    product_image_crud_mock.list_product_images = AsyncMock(return_value=[])
    product_image_crud_mock.list_product_images_by_job = AsyncMock(
        return_value=[])
    product_image_crud_mock.count_product_images_by_job = AsyncMock(
        return_value=0)
    product_image_crud_mock.list_product_images_by_job_with_features = AsyncMock(
        return_value=[])

    video_frame_crud_mock = MagicMock()
    video_frame_crud_mock.create_video_frame = AsyncMock(
        return_value="new_frame_id")
    video_frame_crud_mock.update_embeddings = AsyncMock()
    video_frame_crud_mock.get_video_frame = AsyncMock(return_value=None)
    video_frame_crud_mock.list_video_frames = AsyncMock(return_value=[])
    video_frame_crud_mock.list_video_frames_by_video = AsyncMock(
        return_value=[])
    video_frame_crud_mock.count_video_frames_by_video = AsyncMock(
        return_value=0)
    video_frame_crud_mock.count_video_frames_by_job = AsyncMock(return_value=0)
    video_frame_crud_mock.list_video_frames_by_job_with_features = AsyncMock(
        return_value=[])
    video_frame_crud_mock.get_video_frames_count = AsyncMock(return_value=0)

    product_crud_mock = MagicMock()
    product_crud_mock.create_product = AsyncMock(return_value="new_product_id")
    product_crud_mock.get_product = AsyncMock(return_value=None)
    product_crud_mock.list_products = AsyncMock(return_value=[])

    video_crud_mock = MagicMock()
    video_crud_mock.create_video = AsyncMock(return_value="new_video_id")
    video_crud_mock.get_video = AsyncMock(return_value=None)
    video_crud_mock.list_videos = AsyncMock(return_value=[])
    video_crud_mock.list_videos_by_job = AsyncMock(return_value=[])
    video_crud_mock.count_videos_by_job = AsyncMock(return_value=0)

    job_service_mock = AsyncMock(spec=JobService)
    job_management_service_mock = AsyncMock(spec=JobManagementService)
    db_mock = AsyncMock(spec=DatabaseManager)
    broker_mock = AsyncMock(spec=MessageBroker)

    # Set job_service_mock's job_management_service attribute to the mock
    job_service_mock.job_management_service = job_management_service_mock

    # Import dependency functions from the endpoint modules
    from api import dependency

    # Override dependencies in the FastAPI app by replacing the dependency functions
    app.dependency_overrides[dependency.get_db] = lambda: db_mock
    app.dependency_overrides[dependency.get_broker] = lambda: broker_mock
    app.dependency_overrides[dependency.get_job_service] = lambda: job_service_mock
    app.dependency_overrides[dependency.get_product_image_crud] = lambda: product_image_crud_mock
    app.dependency_overrides[dependency.get_video_frame_crud] = lambda: video_frame_crud_mock
    app.dependency_overrides[dependency.get_product_crud] = lambda: product_crud_mock
    app.dependency_overrides[dependency.get_video_crud] = lambda: video_crud_mock

    # Configure mock job service and job management service
    # Create mock job status return value
    from models.schemas import JobStatusResponse
    mock_job_status = JobStatusResponse(
        job_id="test_job_id",
        phase="completed",
        percent=100.0,
        counts={"products": 0, "videos": 0, "images": 0, "frames": 0},
        updated_at=datetime.now(timezone.utc)
    )
    job_service_mock.get_job_status = AsyncMock(return_value=mock_job_status)
    job_management_service_mock.get_job_status = AsyncMock(
        return_value=mock_job_status)

    # Mock database fetch_one method for direct DB queries
    db_mock.fetch_one = AsyncMock(
        return_value={"updated_at": datetime.now(timezone.utc)})

    # The get_job_or_404 function checks if job_status.phase == "unknown" for job not found
    # This matches the job management service logic which returns phase="unknown" when job is not found
    product_image_crud_mock.count_product_images_by_job.side_effect = [
        10, 5, 3, 2]  # For summary test
    product_image_crud_mock.list_product_images_by_job_with_features.return_value = [
        MagicMock(
            img_id="img1", product_id="prod1",
            masked_local_path="/path/to/segment.png",
            emb_rgb=b"some_embedding", emb_gray=None,
            kp_blob_path="/path/to/keypoints.json",
            updated_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
    ]  # noqa: F821
    product_image_crud_mock.get_product_image.return_value = MagicMock(  # noqa: F821
        img_id="test_img_id", product_id="prod1",
        masked_local_path="/path/to/segment.png",
        emb_rgb=b"some_embedding", emb_gray=None,
        kp_blob_path="/path/to/keypoints.json",
        updated_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc))

    # Configure mock video frame CRUD (specific for test_features_endpoints)
    video_frame_crud_mock.count_video_frames_by_job.side_effect = [
        20, 10, 6, 4]  # For summary test
    video_frame_crud_mock.list_video_frames_by_job_with_features.return_value = [
        MagicMock(frame_id="frame1", video_id="video1", ts=1.23,
                  masked_local_path="/path/to/frame_segment.png",
                  emb_rgb=b"some_embedding", emb_gray=None,
                  kp_blob_path="/path/to/frame_keypoints.json",
                  updated_at=datetime.now(timezone.utc), created_at=datetime.now(timezone.utc))]
    video_frame_crud_mock.get_video_frame.return_value = MagicMock(
        frame_id="test_frame_id", video_id="video1", ts=1.23,
        masked_local_path="/path/to/frame_segment.png",
        emb_rgb=b"some_embedding", emb_gray=None,
        kp_blob_path="/path/to/frame_keypoints.json",
        updated_at=datetime.now(timezone.utc), created_at=datetime.now(timezone.utc))

    yield  # Run the test

    # Clear overrides after the test
    app.dependency_overrides = {}

# Test for GET /jobs/{job_id}/features/summary


@pytest.mark.asyncio
async def test_get_features_summary_success():
    job_id = "test_job_id"
    mock_updated_at = datetime.now(timezone.utc)

    # Re-configure mocks for this specific test, as side_effect might have been consumed
    from models.schemas import JobStatusResponse
    mock_job_status = JobStatusResponse(
        job_id=job_id,
        phase="completed",
        percent=100.0,
        counts={"products": 0, "videos": 0, "images": 0, "frames": 0},
        updated_at=mock_updated_at
    )
    job_service_mock.get_job_status.return_value = mock_job_status  # noqa: F821
    product_image_crud_mock.count_product_images_by_job.side_effect = [  # noqa: F821
        10, 5, 3, 2]
    video_frame_crud_mock.count_video_frames_by_job.side_effect = [  # noqa: F821
        20, 10, 6, 4]
    db_mock.fetch_one.return_value = {"updated_at": mock_updated_at}  # noqa: F821

    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
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
    assert response_updated_at.replace(
        tzinfo=None) == expected_updated_at.replace(tzinfo=None)


@pytest.mark.asyncio
async def test_get_features_summary_job_not_found():
    job_id = "non_existent_job"
    from models.schemas import JobStatusResponse
    mock_job_status = JobStatusResponse(
        job_id=job_id,
        phase="unknown",
        percent=0.0,
        counts={"products": 0, "videos": 0, "images": 0, "frames": 0},
        updated_at=None
    )
    job_service_mock.get_job_status.return_value = mock_job_status  # noqa: F821

    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
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

    from models.schemas import JobStatusResponse
    mock_job_status = JobStatusResponse(
        job_id=job_id,
        phase="completed",
        percent=100.0,
        counts={"products": 0, "videos": 0, "images": 0, "frames": 0},
        updated_at=datetime.now(timezone.utc)
    )
    job_service_mock.get_job_status.return_value = mock_job_status  # noqa: F821
    product_image_crud_mock.list_product_images_by_job_with_features.return_value = [  # noqa: F821
        mock_image]
    # Reset the side_effect and set a direct return value for this test
    product_image_crud_mock.count_product_images_by_job = AsyncMock(  # noqa: F821
        return_value=1)

    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
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
    assert item["updated_at"] == get_gmt7_time(
        mock_image.updated_at).isoformat().replace("+07:00", "+07:00")


@pytest.mark.asyncio
async def test_get_job_product_images_features_job_not_found():
    job_id = "non_existent_job"
    from models.schemas import JobStatusResponse
    mock_job_status = JobStatusResponse(
        job_id=job_id,
        phase="unknown",
        percent=0.0,
        counts={"products": 0, "videos": 0, "images": 0, "frames": 0},
        updated_at=None
    )
    job_service_mock.get_job_status.return_value = mock_job_status  # noqa: F821

    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
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
    mock_frame.kp_blob_path = "/path/to/keypoints.json"
    mock_frame.updated_at = datetime.now(timezone.utc)
    mock_frame.created_at = datetime.now(timezone.utc)

    from models.schemas import JobStatusResponse
    mock_job_status = JobStatusResponse(
        job_id=job_id,
        phase="completed",
        percent=100.0,
        counts={"products": 0, "videos": 0, "images": 0, "frames": 0},
        updated_at=datetime.now(timezone.utc)
    )
    job_service_mock.get_job_status.return_value = mock_job_status  # noqa: F821
    video_frame_crud_mock.list_video_frames_by_job_with_features.return_value = [  # noqa: F821
        mock_frame]
    video_frame_crud_mock.count_video_frames_by_job = AsyncMock(return_value=1)  # noqa: F821

    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
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
    assert item["paths"]["keypoints"] == "/path/to/keypoints.json"
    assert item["updated_at"] == get_gmt7_time(
        mock_frame.updated_at).isoformat().replace("+07:00", "+07:00")


@pytest.mark.asyncio
async def test_get_job_video_frames_features_job_not_found():
    job_id = "non_existent_job"
    from models.schemas import JobStatusResponse
    mock_job_status = JobStatusResponse(
        job_id=job_id,
        phase="unknown",
        percent=0.0,
        counts={"products": 0, "videos": 0, "images": 0, "frames": 0},
        updated_at=None
    )
    job_service_mock.get_job_status.return_value = mock_job_status  # noqa: F821

    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
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

    product_image_crud_mock.get_product_image = AsyncMock(  # noqa: F821
        return_value=mock_image)

    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
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
    assert data["updated_at"] == get_gmt7_time(
        mock_image.updated_at).isoformat().replace("+07:00", "+07:00")


@pytest.mark.asyncio
async def test_get_product_image_feature_not_found():
    img_id = "non_existent_img"
    product_image_crud_mock.get_product_image = AsyncMock(return_value=None)  # noqa: F821

    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
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

    video_frame_crud_mock.get_video_frame = AsyncMock(return_value=mock_frame)  # noqa: F821

    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
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
    assert data["updated_at"] == get_gmt7_time(
        mock_frame.updated_at).isoformat().replace("+07:00", "+07:00")


@pytest.mark.asyncio
async def test_get_video_frame_feature_not_found():
    frame_id = "non_existent_frame"
    video_frame_crud_mock.get_video_frame = AsyncMock(return_value=None)  # noqa: F821

    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
        response = await ac.get(f"/features/video-frames/{frame_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Video frame {frame_id} not found"}
