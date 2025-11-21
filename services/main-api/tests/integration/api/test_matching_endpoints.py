import pytest
import uuid
from httpx import AsyncClient
from common_py.db.models import Job


@pytest.mark.asyncio
async def test_matching_summary_endpoint(test_client: AsyncClient, test_db):
    """Test GET /jobs/{job_id}/matching/summary endpoint"""
    job_id = str(uuid.uuid4())
    
    # Create a test job in matching phase
    job = Job(
        job_id=job_id,
        query="test query",
        phase="matching",
        percent=75,
        status="running"
    )
    test_db.add(job)
    await test_db.commit()
    
    # Test the endpoint
    response = await test_client.get(f"/jobs/{job_id}/matching/summary")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert data["job_id"] == job_id
    assert data["status"] in ["pending", "running", "completed", "failed"]
    assert "candidates_total" in data
    assert "candidates_processed" in data
    assert "matches_found" in data
    assert "matches_with_evidence" in data
    assert isinstance(data["blockers"], list)


@pytest.mark.asyncio
async def test_matching_summary_not_found(test_client: AsyncClient):
    """Test matching summary endpoint with non-existent job"""
    fake_job_id = str(uuid.uuid4())
    
    response = await test_client.get(f"/jobs/{fake_job_id}/matching/summary")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_matching_summary_force_refresh(
    test_client: AsyncClient,
    test_db
):
    """Test matching summary with force_refresh parameter"""
    job_id = str(uuid.uuid4())
    
    job = Job(
        job_id=job_id,
        query="test query",
        phase="completed",
        percent=100,
        status="completed"
    )
    test_db.add(job)
    await test_db.commit()
    
    response = await test_client.get(
        f"/jobs/{job_id}/matching/summary",
        params={"force_refresh": True}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
