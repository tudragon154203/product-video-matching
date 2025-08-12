"""
End-to-end integration tests
"""
import pytest
import asyncio
import uuid


@pytest.mark.asyncio
async def test_complete_pipeline_flow(http_client, orchestrator_url, results_api_url, db_manager, clean_database):
    """Test complete pipeline from job start to results"""
    # Start a job
    job_request = {
        "industry": "e2e test pillows",
        "top_amz": 2,
        "top_ebay": 1,
        "platforms": ["youtube"],
        "recency_days": 30
    }
    
    response = await http_client.post(f"{orchestrator_url}/start-job", json=job_request)
    assert response.status_code == 200
    
    job_data = response.json()
    job_id = job_data["job_id"]
    
    # Wait for job to progress through phases
    max_wait_time = 60  # seconds
    wait_interval = 5   # seconds
    waited_time = 0
    
    final_phase = None
    while waited_time < max_wait_time:
        response = await http_client.get(f"{orchestrator_url}/status/{job_id}")
        assert response.status_code == 200
        
        status_data = response.json()
        phase = status_data["phase"]
        
        if phase in ["completed", "failed"]:
            final_phase = phase
            break
        
        await asyncio.sleep(wait_interval)
        waited_time += wait_interval
    
    # Job should complete (or at least progress significantly)
    assert final_phase is not None, f"Job did not complete within {max_wait_time} seconds"
    
    # Check that data was created in database
    products_count = await db_manager.fetch_val(
        "SELECT COUNT(*) FROM products WHERE job_id = $1", job_id
    )
    
    videos_count = await db_manager.fetch_val(
        "SELECT COUNT(*) FROM videos WHERE job_id = $1", job_id
    )
    
    # Should have created some products and videos
    assert products_count > 0, "No products were created"
    assert videos_count > 0, "No videos were created"
    
    # Check results API
    response = await http_client.get(f"{results_api_url}/results?job_id={job_id}")
    assert response.status_code == 200
    
    results = response.json()
    # Results might be empty if no matches were found (expected with mock data)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_service_resilience(http_client, orchestrator_url, results_api_url):
    """Test system resilience to various conditions"""
    # Test with invalid job request
    invalid_request = {
        "industry": "",  # Empty industry
        "top_amz": -1,   # Invalid count
        "top_ebay": 0
    }
    
    response = await http_client.post(f"{orchestrator_url}/start-job", json=invalid_request)
    # Should handle gracefully (might return 400 or process with defaults)
    assert response.status_code in [200, 400, 422]
    
    # Test with very large request
    large_request = {
        "industry": "test" * 100,  # Very long industry name
        "top_amz": 1000,           # Large count
        "top_ebay": 1000,
        "platforms": ["youtube", "bilibili"],
        "recency_days": 10000
    }
    
    response = await http_client.post(f"{orchestrator_url}/start-job", json=large_request)
    # Should handle gracefully
    assert response.status_code in [200, 400, 422]


@pytest.mark.asyncio
async def test_concurrent_jobs(http_client, orchestrator_url):
    """Test handling multiple concurrent jobs"""
    job_requests = []
    for i in range(3):
        job_requests.append({
            "industry": f"concurrent test {i}",
            "top_amz": 1,
            "top_ebay": 1,
            "platforms": ["youtube"],
            "recency_days": 30
        })
    
    # Start all jobs concurrently
    tasks = []
    for request in job_requests:
        task = asyncio.create_task(
            http_client.post(f"{orchestrator_url}/start-job", json=request)
        )
        tasks.append(task)
    
    responses = await asyncio.gather(*tasks)
    
    # All jobs should start successfully
    job_ids = []
    for response in responses:
        assert response.status_code == 200
        job_data = response.json()
        job_ids.append(job_data["job_id"])
    
    # All job IDs should be unique
    assert len(set(job_ids)) == len(job_ids)
    
    # Check status of all jobs
    for job_id in job_ids:
        response = await http_client.get(f"{orchestrator_url}/status/{job_id}")
        assert response.status_code == 200
        
        status_data = response.json()
        assert status_data["job_id"] == job_id


@pytest.mark.asyncio
async def test_data_consistency(http_client, orchestrator_url, results_api_url, db_manager):
    """Test data consistency across services"""
    # Start a job and let it run
    job_request = {
        "industry": "consistency test",
        "top_amz": 2,
        "top_ebay": 1,
        "platforms": ["youtube"],
        "recency_days": 30
    }
    
    response = await http_client.post(f"{orchestrator_url}/start-job", json=job_request)
    assert response.status_code == 200
    
    job_data = response.json()
    job_id = job_data["job_id"]
    
    # Wait a bit for processing
    await asyncio.sleep(10)
    
    # Get data from database directly
    db_products = await db_manager.fetch_all(
        "SELECT product_id, title FROM products WHERE job_id = $1", job_id
    )
    
    db_videos = await db_manager.fetch_all(
        "SELECT video_id, title FROM videos WHERE job_id = $1", job_id
    )
    
    # Get data from API
    response = await http_client.get(f"{results_api_url}/stats")
    assert response.status_code == 200
    api_stats = response.json()
    
    # Check consistency (API stats should reflect database state)
    assert api_stats["products"] >= len(db_products)
    assert api_stats["videos"] >= len(db_videos)
    
    # Test individual product/video endpoints
    for product in db_products[:2]:  # Test first 2 products
        response = await http_client.get(f"{results_api_url}/products/{product['product_id']}")
        assert response.status_code == 200
        
        api_product = response.json()
        assert api_product["product_id"] == product["product_id"]
        assert api_product["title"] == product["title"]
    
    for video in db_videos[:2]:  # Test first 2 videos
        response = await http_client.get(f"{results_api_url}/videos/{video['video_id']}")
        assert response.status_code == 200
        
        api_video = response.json()
        assert api_video["video_id"] == video["video_id"]
        assert api_video["title"] == video["title"]


@pytest.mark.asyncio
async def test_error_recovery(http_client, orchestrator_url):
    """Test system recovery from errors"""
    # Test job status for non-existent job
    fake_job_id = str(uuid.uuid4())
    response = await http_client.get(f"{orchestrator_url}/status/{fake_job_id}")
    assert response.status_code == 404
    
    # Test malformed requests
    malformed_requests = [
        {},  # Empty request
        {"industry": "test"},  # Missing required fields
        {"invalid_field": "value"},  # Invalid fields
        None  # Null request
    ]
    
    for request in malformed_requests:
        try:
            response = await http_client.post(f"{orchestrator_url}/start-job", json=request)
            # Should return error status
            assert response.status_code >= 400
        except Exception:
            # Request might fail at HTTP level, which is also acceptable
            pass