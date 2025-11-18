import pytest
from httpx import AsyncClient
from main import app
import uuid


@pytest.mark.asyncio
async def test_cancel_job_endpoint(test_client: AsyncClient, test_db):
    """Test POST /jobs/{job_id}/cancel endpoint"""
    # Create a test job first
    job_id = str(uuid.uuid4())
    await test_db.execute(
        "INSERT INTO jobs (job_id, query, industry, phase) VALUES ($1, $2, $3, $4)",
        job_id, "test query", "furniture", "collection"
    )
    
    # Cancel the job
    response = await test_client.post(
        f"/jobs/{job_id}/cancel",
        json={"reason": "test_cancellation", "notes": "Integration test"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["phase"] == "cancelled"
    assert data["reason"] == "test_cancellation"
    assert data["notes"] == "Integration test"
    
    # Verify database state
    job = await test_db.fetch_one("SELECT * FROM jobs WHERE job_id = $1", job_id)
    assert job["phase"] == "cancelled"
    assert job["cancelled_at"] is not None


@pytest.mark.asyncio
async def test_cancel_nonexistent_job(test_client: AsyncClient):
    """Test cancelling a job that doesn't exist"""
    fake_job_id = str(uuid.uuid4())
    
    response = await test_client.post(
        f"/jobs/{fake_job_id}/cancel",
        json={"reason": "test"}
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_job_idempotent(test_client: AsyncClient, test_db):
    """Test that cancelling the same job twice is idempotent"""
    job_id = str(uuid.uuid4())
    await test_db.execute(
        "INSERT INTO jobs (job_id, query, industry, phase) VALUES ($1, $2, $3, $4)",
        job_id, "test query", "furniture", "collection"
    )
    
    # First cancellation
    response1 = await test_client.post(
        f"/jobs/{job_id}/cancel",
        json={"reason": "first_cancel"}
    )
    assert response1.status_code == 200
    
    # Second cancellation
    response2 = await test_client.post(
        f"/jobs/{job_id}/cancel",
        json={"reason": "second_cancel"}
    )
    assert response2.status_code == 200
    
    # Should return the original cancellation info
    data = response2.json()
    assert data["phase"] == "cancelled"


@pytest.mark.asyncio
async def test_delete_job_endpoint(test_client: AsyncClient, test_db):
    """Test DELETE /jobs/{job_id} endpoint"""
    job_id = str(uuid.uuid4())
    await test_db.execute(
        "INSERT INTO jobs (job_id, query, industry, phase) VALUES ($1, $2, $3, $4)",
        job_id, "test query", "furniture", "completed"
    )
    
    # Delete the job
    response = await test_client.delete(f"/jobs/{job_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["status"] == "deleted"
    
    # Verify database state
    job = await test_db.fetch_one("SELECT * FROM jobs WHERE job_id = $1", job_id)
    assert job["deleted_at"] is not None


@pytest.mark.asyncio
async def test_delete_active_job_without_force(test_client: AsyncClient, test_db):
    """Test deleting active job without force flag returns 409"""
    job_id = str(uuid.uuid4())
    await test_db.execute(
        "INSERT INTO jobs (job_id, query, industry, phase) VALUES ($1, $2, $3, $4)",
        job_id, "test query", "furniture", "collection"
    )
    
    response = await test_client.delete(f"/jobs/{job_id}")
    
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_delete_active_job_with_force(test_client: AsyncClient, test_db):
    """Test deleting active job with force flag"""
    job_id = str(uuid.uuid4())
    await test_db.execute(
        "INSERT INTO jobs (job_id, query, industry, phase) VALUES ($1, $2, $3, $4)",
        job_id, "test query", "furniture", "collection"
    )
    
    response = await test_client.delete(f"/jobs/{job_id}?force=true")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deleted"


@pytest.mark.asyncio
async def test_list_jobs_includes_cancellation_info(test_client: AsyncClient, test_db):
    """Test that list jobs endpoint includes cancellation timestamps"""
    job_id = str(uuid.uuid4())
    await test_db.execute(
        "INSERT INTO jobs (job_id, query, industry, phase, cancelled_at) VALUES ($1, $2, $3, $4, NOW())",
        job_id, "test query", "furniture", "cancelled"
    )
    
    response = await test_client.get("/jobs")
    
    assert response.status_code == 200
    data = response.json()
    
    # Find our test job
    test_job = next((j for j in data["items"] if j["job_id"] == job_id), None)
    assert test_job is not None
    assert test_job["phase"] == "cancelled"
    assert test_job["cancelled_at"] is not None
