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

@pytest.fixture
def client():
    """Fixture to create a TestClient for the FastAPI app."""
    return TestClient(main.app)

@pytest.fixture
def mock_db_instances():
    """Fixture to mock global database and CRUD instances."""
    with patch('api.image_endpoints.job_service_instance', new_callable=AsyncMock) as mock_job_service, \
         patch('api.image_endpoints.product_image_crud_instance', new_callable=AsyncMock) as mock_product_image_crud, \
         patch('api.image_endpoints.product_crud_instance', new_callable=AsyncMock) as mock_product_crud:
        
        # Configure mock job service
        mock_job_service.get_job.return_value = {"job_id": MOCK_JOB_ID}  # Job exists
        
        # Configure mock product image CRUD
        mock_product_image_crud.list_product_images_by_job.return_value = [
            MockProductImage(MOCK_IMAGE_ID_1, MOCK_PRODUCT_ID_1, "/path/to/image1.jpg", "Product Title 1", datetime.now() - timedelta(days=5)),
            MockProductImage(MOCK_IMAGE_ID_2, MOCK_PRODUCT_ID_2, "/path/to/image2.jpg", "Another Product", datetime.now() - timedelta(days=10))
        ]
        mock_product_image_crud.count_product_images_by_job.return_value = 2
        
        yield mock_job_service, mock_product_image_crud, mock_product_crud

def test_get_job_images_success(client, mock_db_instances):
    """Test GET /jobs/{job_id}/images with success."""
    response = client.get(f"/jobs/{MOCK_JOB_ID}/images")
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

def test_get_job_images_not_found(client, mock_db_instances):
    """Test GET /jobs/{job_id}/images for job not found."""
    mock_db_instances[0].get_job.return_value = None  # Mock job_service_instance.get_job
    response = client.get(f"/jobs/nonexistent_job/images")
    if response.status_code != 404:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 404
    assert "Job nonexistent_job not found" in response.json()["detail"]
    print("✓ test_get_job_images_not_found passed")

def test_get_job_images_with_product_id_filter(client, mock_db_instances):
    """Test GET /jobs/{job_id}/images with product_id filter."""
    mock_db_instances[1].list_product_images_by_job.return_value = [
        MockProductImage(MOCK_IMAGE_ID_1, MOCK_PRODUCT_ID_1, "/path/to/image1.jpg", "Product Title 1", datetime.now())
    ]
    mock_db_instances[1].count_product_images_by_job.return_value = 1
    
    params = {
        "product_id": MOCK_PRODUCT_ID_1
    }
    response = client.get(f"/jobs/{MOCK_JOB_ID}/images", params=params)
    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["product_id"] == MOCK_PRODUCT_ID_1
    print("✓ test_get_job_images_with_product_id_filter passed")

def test_get_job_images_with_search_query(client, mock_db_instances):
    """Test GET /jobs/{job_id}/images with search query."""
    mock_db_instances[1].list_product_images_by_job.return_value = [
        MockProductImage(MOCK_IMAGE_ID_1, MOCK_PRODUCT_ID_1, "/path/to/image1.jpg", "Specific Product Title", datetime.now())
    ]
    mock_db_instances[1].count_product_images_by_job.return_value = 1
    
    params = {
        "q": "Specific"
    }
    response = client.get(f"/jobs/{MOCK_JOB_ID}/images", params=params)
    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["product_title"] == "Specific Product Title"
    print("✓ test_get_job_images_with_search_query passed")

def test_get_job_images_with_pagination(client, mock_db_instances):
    """Test GET /jobs/{job_id}/images with pagination."""
    mock_db_instances[1].list_product_images_by_job.return_value = [
        MockProductImage(MOCK_IMAGE_ID_1, MOCK_PRODUCT_ID_1, "/path/to/image1.jpg", "Product Title 1", datetime.now())
    ]
    mock_db_instances[1].count_product_images_by_job.return_value = 1
    
    params = {
        "limit": 1,
        "offset": 0
    }
    response = client.get(f"/jobs/{MOCK_JOB_ID}/images", params=params)
    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["limit"] == 1
    assert data["offset"] == 0
    print("✓ test_get_job_images_with_pagination passed")

def test_get_job_images_with_sorting(client, mock_db_instances):
    """Test GET /jobs/{job_id}/images with sorting."""
    mock_db_instances[1].list_product_images_by_job.return_value = [
        MockProductImage(MOCK_IMAGE_ID_1, MOCK_PRODUCT_ID_1, "/path/to/image1.jpg", "Product Title 1", datetime.now())
    ]
    mock_db_instances[1].count_product_images_by_job.return_value = 1
    
    params = {
        "sort_by": "img_id",
        "order": "ASC"
    }
    response = client.get(f"/jobs/{MOCK_JOB_ID}/images", params=params)
    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    print("✓ test_get_job_images_with_sorting passed")

def test_get_job_images_invalid_sort_by(client, mock_db_instances):
    """Test GET /jobs/{job_id}/images with invalid sort_by parameter."""
    params = {
        "sort_by": "invalid_field",
        "order": "ASC"
    }
    response = client.get(f"/jobs/{MOCK_JOB_ID}/images", params=params)
    # Should return 422 due to validation error
    assert response.status_code == 422
    print("✓ test_get_job_images_invalid_sort_by passed")

def test_get_job_images_invalid_order(client, mock_db_instances):
    """Test GET /jobs/{job_id}/images with invalid order parameter."""
    params = {
        "sort_by": "img_id",
        "order": "INVALID"
    }
    response = client.get(f"/jobs/{MOCK_JOB_ID}/images", params=params)
    # Should return 422 due to validation error
    assert response.status_code == 422
    print("✓ test_get_job_images_invalid_order passed")