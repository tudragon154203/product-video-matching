from main import app # Import app directly
from httpx import AsyncClient  # Use AsyncClient for async tests
import pytz
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
pytestmark = pytest.mark.integration

# Import dependencies that will be mocked

# Mock data
MOCK_JOB_ID = "job123"
MOCK_PRODUCT_ID_1 = "product1"
MOCK_PRODUCT_ID_2 = "product2"
MOCK_IMAGE_ID_1 = "image1"
MOCK_IMAGE_ID_2 = "image2"

# Mock ProductImage model (simplified for testing)


class MockProductImage:
    def __init__(self, img_id, product_id, local_path, product_title, created_at, updated_at=None):
        self.img_id = img_id
        self.product_id = product_id
        self.local_path = local_path
        self.product_title = product_title
        self.created_at = created_at
        self.updated_at = updated_at if updated_at else created_at

# Helper to convert datetime to GMT+7


def to_gmt7(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(pytz.timezone('Asia/Saigon'))


# Global mock instances (will be set by setup_mocks fixture)
job_service_mock: JobService  # noqa: F821
# New mock for JobManagementService
job_management_service_mock: JobManagementService  # noqa: F821
product_image_crud_mock: ProductImageCRUD  # noqa: F821
product_crud_mock: ProductCRUD  # noqa: F821
db_mock: DatabaseHandler  # noqa: F821
broker_mock: MessageBroker  # noqa: F821


@pytest.fixture(autouse=True)
def setup_mocks(monkeypatch):  # Add monkeypatch as an argument
    global job_service_mock, job_management_service_mock, product_image_crud_mock, product_crud_mock, db_mock, broker_mock

    # Set environment variables for tests
    monkeypatch.setenv(
        "POSTGRES_DSN", "postgresql://user:password@host:port/database")
    monkeypatch.setenv("BUS_BROKER", "amqp://guest:guest@localhost:5672/")

    # Initialize mocks with default return values
    job_service_mock = AsyncMock(spec=JobService)
    job_management_service_mock = AsyncMock(spec=JobManagementService)

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

    product_crud_mock = MagicMock()
    product_crud_mock.create_product = AsyncMock(return_value="new_product_id")
    product_crud_mock.get_product = AsyncMock(return_value=None)
    product_crud_mock.list_products = AsyncMock(return_value=[])

    db_mock = AsyncMock(spec=DatabaseManager)
    broker_mock = AsyncMock(spec=MessageBroker)

    # Set job_service_mock's job_management_service attribute to the mock
    job_service_mock.job_management_service = job_management_service_mock

    # Import dependency functions from the endpoint modules
    from api.image_endpoints import get_db, get_broker, get_job_service, get_product_image_crud, get_product_crud

    # Override dependencies in the FastAPI app by replacing the dependency functions
    app.dependency_overrides[get_db] = lambda: db_mock
    app.dependency_overrides[get_broker] = lambda: broker_mock
    app.dependency_overrides[get_job_service] = lambda: job_service_mock
    app.dependency_overrides[get_product_image_crud] = lambda: product_image_crud_mock
    app.dependency_overrides[get_product_crud] = lambda: product_crud_mock

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
    job_management_service_mock.get_job_status = AsyncMock(
        return_value=mock_job_status)

    # Configure mock product image CRUD (specific for test_image_endpoints)
    product_image_crud_mock.list_product_images_by_job.return_value = [
        MockProductImage(MOCK_IMAGE_ID_1, MOCK_PRODUCT_ID_1, "/path/to/image1.jpg",
                         "Product Title 1", datetime.now(timezone.utc) - timedelta(days=5)),
        MockProductImage(MOCK_IMAGE_ID_2, MOCK_PRODUCT_ID_2, "/path/to/image2.jpg",
                         "Another Product", datetime.now(timezone.utc) - timedelta(days=10))
    ]
    product_image_crud_mock.count_product_images_by_job.return_value = 2

    yield  # Run the test

    # Clear overrides after the test
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_get_job_images_success():
    """Test GET /jobs/{job_id}/images with success."""
    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
        response = await ac.get(f"/jobs/{MOCK_JOB_ID}/images")

    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["img_id"] == MOCK_IMAGE_ID_1
    assert "updated_at" in data["items"][0]
    # Check if updated_at is in GMT+7 (Asia/Saigon)
    assert data["items"][0]["updated_at"].endswith("+07:00")
    print("✓ test_get_job_images_success passed")


@pytest.mark.asyncio
async def test_get_job_images_not_found():
    """Test GET /jobs/{job_id}/images for job not found."""
    from models.schemas import JobStatusResponse
    nonexistent_job = "nonexistent_job"  # Define the variable
    mock_job_status = JobStatusResponse(
        job_id=nonexistent_job,
        phase="unknown",
        percent=0.0,
        counts={"products": 0, "videos": 0, "images": 0, "frames": 0},
        updated_at=None
    )
    job_service_mock.get_job_status.return_value = mock_job_status
    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
        response = await ac.get(f"/jobs/{nonexistent_job}/images")

    if response.status_code != 404:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 404
    assert "Job nonexistent_job not found" in response.json()["detail"]
    print("✓ test_get_job_images_not_found passed")


@pytest.mark.asyncio
async def test_get_job_images_with_product_id_filter():
    """Test GET /jobs/{job_id}/images with product_id filter."""
    product_image_crud_mock.list_product_images_by_job.return_value = [
        MockProductImage(MOCK_IMAGE_ID_1, MOCK_PRODUCT_ID_1,
                         "/path/to/image1.jpg", "Product Title 1", datetime.now())
    ]
    product_image_crud_mock.count_product_images_by_job.return_value = 1

    params = {
        "product_id": MOCK_PRODUCT_ID_1
    }
    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
        response = await ac.get(f"/jobs/{MOCK_JOB_ID}/images", params=params)

    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["product_id"] == MOCK_PRODUCT_ID_1
    print("✓ test_get_job_images_with_product_id_filter passed")


@pytest.mark.asyncio
async def test_get_job_images_with_search_query():
    """Test GET /jobs/{job_id}/images with search query."""
    product_image_crud_mock.list_product_images_by_job.return_value = [
        MockProductImage(MOCK_IMAGE_ID_1, MOCK_PRODUCT_ID_1,
                         "/path/to/image1.jpg", "Specific Product Title", datetime.now())
    ]
    product_image_crud_mock.count_product_images_by_job.return_value = 1

    params = {
        "q": "Specific"
    }
    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
        response = await ac.get(f"/jobs/{MOCK_JOB_ID}/images", params=params)

    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["product_title"] == "Specific Product Title"
    print("✓ test_get_job_images_with_search_query passed")


@pytest.mark.asyncio
async def test_get_job_images_with_pagination():
    """Test GET /jobs/{job_id}/images with pagination."""
    product_image_crud_mock.list_product_images_by_job.return_value = [
        MockProductImage(MOCK_IMAGE_ID_1, MOCK_PRODUCT_ID_1,
                         "/path/to/image1.jpg", "Product Title 1", datetime.now())
    ]
    product_image_crud_mock.count_product_images_by_job.return_value = 1

    params = {
        "limit": 1,
        "offset": 0
    }
    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
        response = await ac.get(f"/jobs/{MOCK_JOB_ID}/images", params=params)

    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["limit"] == 1
    assert data["offset"] == 0
    print("✓ test_get_job_images_with_pagination passed")


@pytest.mark.asyncio
async def test_get_job_images_with_sorting():
    """Test GET /jobs/{job_id}/images with sorting."""
    product_image_crud_mock.list_product_images_by_job.return_value = [
        MockProductImage(MOCK_IMAGE_ID_1, MOCK_PRODUCT_ID_1,
                         "/path/to/image1.jpg", "Product Title 1", datetime.now())
    ]
    product_image_crud_mock.count_product_images_by_job.return_value = 1

    params = {
        "sort_by": "img_id",
        "order": "ASC"
    }
    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
        response = await ac.get(f"/jobs/{MOCK_JOB_ID}/images", params=params)

    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    print("✓ test_get_job_images_with_sorting passed")


@pytest.mark.asyncio
async def test_get_job_images_invalid_sort_by():
    """Test GET /jobs/{job_id}/images with invalid sort_by parameter."""
    params = {
        "sort_by": "invalid_field",
        "order": "ASC"
    }
    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
        response = await ac.get(f"/jobs/{MOCK_JOB_ID}/images", params=params)

    # Should return 422 due to validation error
    assert response.status_code == 422
    print("✓ test_get_job_images_invalid_sort_by passed")


@pytest.mark.asyncio
async def test_get_job_images_invalid_order():
    """Test GET /jobs/{job_id}/images with invalid order parameter."""
    params = {
        "sort_by": "img_id",
        "order": "INVALID"
    }
    async with AsyncClient(app=app, base_url="http://localhost:8888") as ac:
        response = await ac.get(f"/jobs/{MOCK_JOB_ID}/images", params=params)

    # Should return 422 due to validation error
    assert response.status_code == 422
    print("✓ test_get_job_images_invalid_order passed")
