#!/usr/bin/env python3
"""
End-to-end smoke test for the product-video matching system
"""
import asyncio
import httpx
import time
import os
import sys

# Add libs to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'libs'))

from common_py.logging_config import configure_logging
from config import config

logger = configure_logging("smoke-test")

# Service URLs
MAIN_API_URL = config.MAIN_API_URL
RESULTS_API_URL = config.RESULTS_API_URL


async def run_smoke_test():
    """Run end-to-end smoke test
    
    This smoke test verifies critical functionalities of the product-video matching system:
    1. Service health checks
    2. Job initiation and processing
    3. Result generation and validation
    4. API endpoint functionality
    
    Timeout durations have been increased to ensure sufficient time for all critical
    functionalities to complete without premature test failures due to timing issues.
    """
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            logger.info("Starting smoke test...")
            
            # Step 1: Check service health
            await check_service_health(client)
            
            # Step 2: Start a job
            job_id = await start_job(client)
            
            # Step 3: Wait for job completion
            await wait_for_job_completion(client, job_id)
            
            # Step 4: Check results
            await check_results(client, job_id)
            
            # Step 5: Test API endpoints
            await test_api_endpoints(client)
            
            logger.info("Smoke test completed successfully! ✅")
            
    except Exception as e:
        logger.error(f"Smoke test failed: {str(e)}")
        raise


async def check_service_health(client):
    """Check that all services are healthy"""
    logger.info("Checking service health...")
    
    services = [
        ("Main API", f"{MAIN_API_URL}/health"),
        ("Results API", f"{RESULTS_API_URL}/health")
    ]
    
    for service_name, health_url in services:
        try:
            response = await client.get(health_url)
            response.raise_for_status()
            logger.info(f"{service_name} is healthy (status: {response.status_code})")
        except Exception as e:
            logger.error(f"{service_name} health check failed: {str(e)}")
            raise


async def start_job(client):
    """Start a new matching job"""
    logger.info("Starting new job...")
    
    job_request = {
        "query": "gối",
        "top_amz": 3,
        "top_ebay": 2,
        "platforms": ["youtube"],
        "recency_days": 365
    }
    
    response = await client.post(f"{MAIN_API_URL}/start-job", json=job_request)
    response.raise_for_status()
    
    job_data = response.json()
    job_id = job_data["job_id"]
    
    logger.info(f"Job started successfully (job_id: {job_id})")
    return job_id


async def wait_for_job_completion(client, job_id, max_wait_time=500):
    """Wait for job to complete
    
    Args:
        client: HTTP client for API requests
        job_id: ID of the job to wait for
        max_wait_time: Maximum time to wait for job completion in seconds (default: 500)                           
    """
    logger.info(f"Waiting for job completion... (job_id: {job_id})")
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            response = await client.get(f"{MAIN_API_URL}/status/{job_id}")
            response.raise_for_status()
            
            status_data = response.json()
            phase = status_data["phase"]
            percent = status_data["percent"]
            
            logger.info(f"Job progress (job_id: {job_id}, phase: {phase}, percent: {percent})")
            
            if phase == "completed":
                logger.info(f"Job completed successfully (job_id: {job_id})")
                return
            elif phase == "failed":
                raise Exception(f"Job failed: {job_id}")
            
            # Wait before next check
            await asyncio.sleep(5)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.error(f"Job not found (job_id: {job_id})")
                raise
            else:
                logger.warning(f"Status check failed, retrying... ({str(e)})")
                await asyncio.sleep(2)
    
    raise Exception(f"Job did not complete within {max_wait_time} seconds")


async def check_results(client, job_id):
    """Check that results were generated"""
    logger.info(f"Checking results... (job_id: {job_id})")
    
    # Get results for the job
    response = await client.get(f"{RESULTS_API_URL}/results", params={"job_id": job_id})
    response.raise_for_status()
    
    results = response.json()
    
    logger.info(f"Results retrieved (job_id: {job_id}, result_count: {len(results)})")
    
    if len(results) == 0:
        logger.warning("No matches found - this might be expected for mock data")
    else:
        # Check first result
        first_result = results[0]
        logger.info(f"Sample result (match_id: {first_result['match_id']}, "
                   f"score: {first_result['score']}, "
                   f"product_title: {first_result.get('product_title')}, "
                   f"video_title: {first_result.get('video_title')})")
        
        # Verify result structure
        required_fields = ["match_id", "job_id", "product_id", "video_id", "score"]
        for field in required_fields:
            if field not in first_result:
                raise Exception(f"Missing required field in result: {field}")
        
        # Verify score is within valid range
        score = first_result["score"]
        if not (0.0 <= score <= 1.0):
            raise Exception(f"Invalid score range: {score}")
        
        logger.info("Result validation passed")
        
        # Test detailed match endpoint
        match_id = first_result["match_id"]
        response = await client.get(f"{RESULTS_API_URL}/matches/{match_id}")
        response.raise_for_status()
        
        match_detail = response.json()
        logger.info(f"Match detail retrieved (match_id: {match_id})")
        
        # Verify match detail structure
        if "product" not in match_detail or "video" not in match_detail:
            raise Exception("Match detail missing product or video information")


async def test_api_endpoints(http_client):
    """Test various API endpoints"""
    logger.info("Testing API endpoints...")
    
    # Test stats endpoint
    response = await http_client.get(f"{RESULTS_API_URL}/stats")
    response.raise_for_status()
    stats = response.json()
    logger.info(f"System stats: {stats}")
    
    # Test results with filters
    response = await http_client.get(f"{RESULTS_API_URL}/results", params={"min_score": 0.5})
    response.raise_for_status()
    filtered_results = response.json()
    logger.info(f"Filtered results (count: {len(filtered_results)})")


if __name__ == "__main__":
    asyncio.run(run_smoke_test())