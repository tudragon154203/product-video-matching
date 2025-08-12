"""
API integration tests
"""
import pytest
import asyncio
import uuid


@pytest.mark.asyncio
async def test_orchestrator_health(http_client, orchestrator_url):
    """Test orchestrator health endpoint"""
    response = await http_client.get(f"{orchestrator_url}/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "orchestrator"


@pytest.mark.asyncio
async def test_results_api_health(http_client, results_api_url):
    """Test results API health endpoint"""
    response = await http_client.get(f"{results_api_url}/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "results-api"


@pytest.mark.asyncio
async def test_vector_index_health(http_client, vector_index_url):
    """Test vector index health endpoint"""
    response = await http_client.get(f"{vector_index_url}/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "vector-index"


@pytest.mark.asyncio
async def test_start_job_api(http_client, orchestrator_url):
    """Test starting a job via API"""
    job_request = {
        "industry": "test integration pillows",
        "top_amz": 2,
        "top_ebay": 1,
        "platforms": ["youtube"],
        "recency_days": 30
    }
    
    response = await http_client.post(f"{orchestrator_url}/start-job", json=job_request)
    assert response.status_code == 200
    
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "started"
    
    job_id = data["job_id"]
    
    # Check job status
    response = await http_client.get(f"{orchestrator_url}/status/{job_id}")
    assert response.status_code == 200
    
    status_data = response.json()
    assert status_data["job_id"] == job_id
    assert "phase" in status_data
    assert "percent" in status_data
    assert "counts" in status_data


@pytest.mark.asyncio
async def test_results_api_endpoints(http_client, results_api_url, db_manager, clean_database):
    """Test results API endpoints"""
    # Create test data
    job_id = "test_api_job"
    product_id = "test_api_product"
    video_id = "test_api_video"
    match_id = str(uuid.uuid4())
    
    # Insert test data
    await db_manager.execute(
        "INSERT INTO jobs (job_id, industry, status, phase) VALUES ($1, $2, $3, $4)",
        job_id, "test api", "completed", "completed"
    )
    
    await db_manager.execute(
        "INSERT INTO products (product_id, src, asin_or_itemid, title, brand, url, job_id) VALUES ($1, $2, $3, $4, $5, $6, $7)",
        product_id, "amazon", "TEST_API", "Test API Product", "TestBrand", "https://example.com", job_id
    )
    
    await db_manager.execute(
        "INSERT INTO videos (video_id, platform, url, title, duration_s, job_id) VALUES ($1, $2, $3, $4, $5, $6)",
        video_id, "youtube", "https://youtube.com/test", "Test API Video", 120, job_id
    )
    
    img_id = f"{product_id}_img_0"
    frame_id = f"{video_id}_frame_0"
    
    await db_manager.execute(
        "INSERT INTO product_images (img_id, product_id, local_path) VALUES ($1, $2, $3)",
        img_id, product_id, "/test/image.jpg"
    )
    
    await db_manager.execute(
        "INSERT INTO video_frames (frame_id, video_id, ts, local_path) VALUES ($1, $2, $3, $4)",
        frame_id, video_id, 30.0, "/test/frame.jpg"
    )
    
    await db_manager.execute(
        "INSERT INTO matches (match_id, job_id, product_id, video_id, best_img_id, best_frame_id, ts, score) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
        match_id, job_id, product_id, video_id, img_id, frame_id, 30.0, 0.87
    )
    
    # Test results endpoint
    response = await http_client.get(f"{results_api_url}/results")
    assert response.status_code == 200
    
    results = response.json()
    assert isinstance(results, list)
    
    # Find our test result
    test_result = None
    for result in results:
        if result["job_id"] == job_id:
            test_result = result
            break
    
    assert test_result is not None
    assert test_result["score"] == 0.87
    assert test_result["product_title"] == "Test API Product"
    
    # Test filtered results
    response = await http_client.get(f"{results_api_url}/results?min_score=0.8&job_id={job_id}")
    assert response.status_code == 200
    
    filtered_results = response.json()
    assert len(filtered_results) >= 1
    assert all(r["score"] >= 0.8 for r in filtered_results)
    
    # Test product detail endpoint
    response = await http_client.get(f"{results_api_url}/products/{product_id}")
    assert response.status_code == 200
    
    product_detail = response.json()
    assert product_detail["product_id"] == product_id
    assert product_detail["title"] == "Test API Product"
    assert product_detail["image_count"] >= 1
    
    # Test video detail endpoint
    response = await http_client.get(f"{results_api_url}/videos/{video_id}")
    assert response.status_code == 200
    
    video_detail = response.json()
    assert video_detail["video_id"] == video_id
    assert video_detail["title"] == "Test API Video"
    assert video_detail["frame_count"] >= 1
    
    # Test match detail endpoint
    response = await http_client.get(f"{results_api_url}/matches/{match_id}")
    assert response.status_code == 200
    
    match_detail = response.json()
    assert match_detail["match_id"] == match_id
    assert match_detail["score"] == 0.87
    assert "product" in match_detail
    assert "video" in match_detail
    
    # Test stats endpoint
    response = await http_client.get(f"{results_api_url}/stats")
    assert response.status_code == 200
    
    stats = response.json()
    assert "products" in stats
    assert "videos" in stats
    assert "matches" in stats
    assert stats["matches"] >= 1


@pytest.mark.asyncio
async def test_vector_index_api(http_client, vector_index_url):
    """Test vector index API endpoints"""
    # Test stats endpoint
    response = await http_client.get(f"{vector_index_url}/stats")
    assert response.status_code == 200
    
    stats = response.json()
    assert "total_images" in stats
    assert "rgb_indexed" in stats
    assert "gray_indexed" in stats
    
    # Test search endpoint with mock vector
    test_vector = [0.1] * 512  # 512-dimensional test vector
    search_request = {
        "query_vector": test_vector,
        "vector_type": "emb_rgb",
        "top_k": 10
    }
    
    response = await http_client.post(f"{vector_index_url}/search", json=search_request)
    assert response.status_code == 200
    
    search_results = response.json()
    assert "results" in search_results
    assert "total_found" in search_results
    assert isinstance(search_results["results"], list)


@pytest.mark.asyncio
async def test_api_error_handling(http_client, results_api_url):
    """Test API error handling"""
    # Test 404 for non-existent product
    response = await http_client.get(f"{results_api_url}/products/nonexistent")
    assert response.status_code == 404
    
    # Test 404 for non-existent video
    response = await http_client.get(f"{results_api_url}/videos/nonexistent")
    assert response.status_code == 404
    
    # Test 404 for non-existent match
    response = await http_client.get(f"{results_api_url}/matches/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_pagination(http_client, results_api_url):
    """Test API pagination"""
    # Test results with limit and offset
    response = await http_client.get(f"{results_api_url}/results?limit=5&offset=0")
    assert response.status_code == 200
    
    results = response.json()
    assert isinstance(results, list)
    assert len(results) <= 5