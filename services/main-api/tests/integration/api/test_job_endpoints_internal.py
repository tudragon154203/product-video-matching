"""
Tests for the new GET /jobs endpoint in job_endpoints.py
"""
from main import app
from unittest.mock import AsyncMock
import httpx
import pytest
pytestmark = pytest.mark.integration

# Import the FastAPI app


@pytest.fixture
def mock_job_service():
    """Mock job service for testing /jobs endpoint"""
    mock_service = AsyncMock()
    mock_service.list_jobs = AsyncMock()
    return mock_service


@pytest.fixture(autouse=True)
def setup_jobs_test_mocks(monkeypatch, mock_job_service):
    """Setup mocks for /jobs endpoint tests"""
    # Set environment variables for tests
    monkeypatch.setenv(
        "POSTGRES_DSN", "postgresql://user:password@host:port/database")
    monkeypatch.setenv("BUS_BROKER", "amqp://guest:guest@localhost:5672/")

    # Import and override dependencies
    from api.job_endpoints import get_db, get_message_broker, get_job_service
    from common_py.database import DatabaseManager
    from common_py.messaging import MessageBroker

    # Create mock dependencies
    db_mock = AsyncMock(spec=DatabaseManager)
    broker_mock = AsyncMock(spec=MessageBroker)

    # Override dependencies
    app.dependency_overrides[get_db] = lambda: db_mock
    app.dependency_overrides[get_message_broker] = lambda: broker_mock
    app.dependency_overrides[get_job_service] = lambda: mock_job_service

    yield

    # Clear overrides after test
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_list_jobs_basic_success():
    """Test basic functionality - successful retrieval of jobs"""
    print("Testing GET /jobs endpoint - basic success...")

    # Mock job service response
    mock_job_service.list_jobs.return_value = (
        [
            {
                "job_id": "job1",
                "query": "ergonomic office chair",
                "industry": "furniture",
                "phase": "completed",
                "created_at": "2023-01-01T10:00:00Z",
                "updated_at": "2023-01-01T10:30:00Z"
            },
            {
                "job_id": "job2",
                "query": "running shoes",
                "industry": "sports",
                "phase": "in_progress",
                "created_at": "2023-01-02T10:00:00Z",
                "updated_at": "2023-01-02T11:00:00Z"
            }
        ],
        2
    )

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/jobs")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data

    # Validate pagination fields
    assert data["total"] == 2
    assert data["limit"] == 50  # default limit
    assert data["offset"] == 0  # default offset

    # Validate job items
    assert len(data["items"]) == 2
    job1 = data["items"][0]
    assert job1["job_id"] == "job1"
    assert job1["query"] == "ergonomic office chair"
    assert job1["industry"] == "furniture"
    assert job1["phase"] == "completed"
    assert job1["created_at"] == "2023-01-01T10:00:00Z"
    assert job1["updated_at"] == "2023-01-01T10:30:00Z"

    job2 = data["items"][1]
    assert job2["job_id"] == "job2"
    assert job2["query"] == "running shoes"
    assert job2["industry"] == "sports"
    assert job2["phase"] == "in_progress"

    print("✓ GET /jobs endpoint basic success test passed")


@pytest.mark.asyncio
async def test_list_jobs_with_pagination():
    """Test pagination parameters (limit and offset)"""
    print("Testing GET /jobs endpoint with pagination...")

    # Mock 5 jobs
    mock_jobs = []
    for i in range(5):
        mock_jobs.append({
            "job_id": f"job{i+1}",
            "query": f"test query {i+1}",
            "industry": "test",
            "phase": "completed",
            "created_at": f"2023-01-0{i+1}T10:00:00Z",
            "updated_at": f"2023-01-0{i+1}T10:30:00Z"
        })

    mock_job_service.list_jobs.return_value = (mock_jobs, 5)

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Test limit parameter
        response = await client.get("/jobs?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["limit"] == 2
        assert data["total"] == 5

        # Test offset parameter
        response = await client.get("/jobs?offset=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["offset"] == 2
        assert data["items"][0]["job_id"] == "job3"  # Third job (offset 2)

        # Test edge case: offset beyond available data
        response = await client.get("/jobs?offset=10&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0
        assert data["offset"] == 10
        assert data["total"] == 5

    print("✓ GET /jobs endpoint pagination test passed")


@pytest.mark.asyncio
async def test_list_jobs_status_filtering():
    """Test status filtering (completed, failed, in_progress)"""
    print("Testing GET /jobs endpoint with status filtering...")

    # Mock jobs with different phases
    mock_jobs = [
        {
            "job_id": "job1",
            "query": "completed job",
            "industry": "test",
            "phase": "completed",
            "created_at": "2023-01-01T10:00:00Z",
            "updated_at": "2023-01-01T10:30:00Z"
        },
        {
            "job_id": "job2",
            "query": "failed job",
            "industry": "test",
            "phase": "failed",
            "created_at": "2023-01-02T10:00:00Z",
            "updated_at": "2023-01-02T10:30:00Z"
        },
        {
            "job_id": "job3",
            "query": "in progress job",
            "industry": "test",
            "phase": "in_progress",
            "created_at": "2023-01-03T10:00:00Z",
            "updated_at": "2023-01-03T10:30:00Z"
        }
    ]

    mock_job_service.list_jobs.return_value = (mock_jobs, 3)

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Test completed filter
        response = await client.get("/jobs?status=completed")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["phase"] == "completed"
        assert data["items"][0]["query"] == "completed job"

        # Test failed filter
        response = await client.get("/jobs?status=failed")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["phase"] == "failed"
        assert data["items"][0]["query"] == "failed job"

        # Test in_progress filter
        response = await client.get("/jobs?status=in_progress")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["phase"] == "in_progress"
        assert data["items"][0]["query"] == "in progress job"

        # Test non-existent status
        response = await client.get("/jobs?status=nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0
        assert data["total"] == 0

    print("✓ GET /jobs endpoint status filtering test passed")


@pytest.mark.asyncio
async def test_list_jobs_ordering():
    """Test ordering (newest first by created_at)"""
    print("Testing GET /jobs endpoint ordering...")

    # Mock jobs out of order (oldest first)
    mock_jobs = [
        {
            "job_id": "job1",
            "query": "oldest job",
            "industry": "test",
            "phase": "completed",
            "created_at": "2023-01-01T10:00:00Z",
            "updated_at": "2023-01-01T10:30:00Z"
        },
        {
            "job_id": "job2",
            "query": "middle job",
            "industry": "test",
            "phase": "completed",
            "created_at": "2023-01-02T10:00:00Z",
            "updated_at": "2023-01-02T10:30:00Z"
        },
        {
            "job_id": "job3",
            "query": "newest job",
            "industry": "test",
            "phase": "completed",
            "created_at": "2023-01-03T10:00:00Z",
            "updated_at": "2023-01-03T10:30:00Z"
        }
    ]

    mock_job_service.list_jobs.return_value = (mock_jobs, 3)

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/jobs")
        assert response.status_code == 200
        data = response.json()

        # Verify ordering (newest first)
        assert data["items"][0]["job_id"] == "job3"  # Newest
        assert data["items"][1]["job_id"] == "job2"  # Middle
        assert data["items"][2]["job_id"] == "job1"  # Oldest

        # Verify timestamps are in descending order
        first_time = data["items"][0]["created_at"]
        second_time = data["items"][1]["created_at"]
        third_time = data["items"][2]["created_at"]

        assert first_time > second_time > third_time

    print("✓ GET /jobs endpoint ordering test passed")


@pytest.mark.asyncio
async def test_list_jobs_empty_results():
    """Test edge case - empty results"""
    print("Testing GET /jobs endpoint with empty results...")

    mock_job_service.list_jobs.return_value = ([], 0)

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/jobs")
        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 0
        assert data["total"] == 0
        assert data["limit"] == 50
        assert data["offset"] == 0

    print("✓ GET /jobs endpoint empty results test passed")


@pytest.mark.asyncio
async def test_list_jobs_invalid_parameters():
    """Test edge cases - invalid parameters"""
    print("Testing GET /jobs endpoint with invalid parameters...")

    mock_job_service.list_jobs.return_value = ([], 0)

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Test negative limit (should use default)
        response = await client.get("/jobs?limit=-5")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 50  # Default value

        # Test zero limit (should use default)
        response = await client.get("/jobs?limit=0")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 50  # Default value

        # Test negative offset (should use default)
        response = await client.get("/jobs?offset=-10")
        assert response.status_code == 200
        data = response.json()
        assert data["offset"] == 0  # Default value

        # Test very large limit (should be capped by endpoint validation)
        response = await client.get("/jobs?limit=200")
        assert response.status_code == 200
        data = response.json()
        # The endpoint should enforce max limit of 100
        assert data["limit"] == 100

    print("✓ GET /jobs endpoint invalid parameters test passed")


@pytest.mark.asyncio
async def test_list_jobs_database_error():
    """Test error handling for database connection issues"""
    print("Testing GET /jobs endpoint with database error...")

    # Mock database error
    mock_job_service.list_jobs.side_effect = Exception(
        "Database connection failed")

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/jobs")
        assert response.status_code == 500
        error_data = response.json()
        assert "detail" in error_data
        assert "Database connection failed" in error_data["detail"]

    print("✓ GET /jobs endpoint database error test passed")


@pytest.mark.asyncio
async def test_list_jobs_combined_filters():
    """Test combining pagination with status filtering"""
    print("Testing GET /jobs endpoint with combined filters...")

    # Mock 10 jobs with different phases
    mock_jobs = []
    for i in range(10):
        phase = "completed" if i % 2 == 0 else "in_progress"
        mock_jobs.append({
            "job_id": f"job{i+1}",
            "query": f"test query {i+1}",
            "industry": "test",
            "phase": phase,
            "created_at": f"2023-01-0{i+1}T10:00:00Z",
            "updated_at": f"2023-01-0{i+1}T10:30:00Z"
        })

    mock_job_service.list_jobs.return_value = (mock_jobs, 10)

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Combine status filter with pagination
        response = await client.get("/jobs?status=completed&limit=3&offset=2")
        assert response.status_code == 200
        data = response.json()

        # Should only get completed jobs
        for job in data["items"]:
            assert job["phase"] == "completed"

        # Should respect pagination
        assert len(data["items"]) <= 3
        assert data["limit"] == 3
        assert data["offset"] == 2
        assert data["total"] == 10  # Total count doesn't respect filter

        # Verify we got the right subset (jobs 5, 7 - completed jobs at offset 2)
        # Every other job starting from offset 2
        expected_job_ids = ["job5", "job7", "job9"]
        actual_job_ids = [job["job_id"] for job in data["items"]]
        assert actual_job_ids == expected_job_ids[:len(actual_job_ids)]

    print("✓ GET /jobs endpoint combined filters test passed")


if __name__ == "__main__":
    # Run tests directly
    import asyncio

    async def run_tests():
        await test_list_jobs_basic_success()
        await test_list_jobs_with_pagination()
        await test_list_jobs_status_filtering()
        await test_list_jobs_ordering()
        await test_list_jobs_empty_results()
        await test_list_jobs_invalid_parameters()
        await test_list_jobs_database_error()
        await test_list_jobs_combined_filters()
        print("All tests passed!")

    asyncio.run(run_tests())
