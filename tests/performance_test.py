#!/usr/bin/env python3
"""
Performance testing script for the product-video matching system
"""
import asyncio
import httpx
import time
import statistics
import os
import sys

# Add libs to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'libs'))

from common_py.logging_config import configure_logging

logger = configure_logging("performance-test")

# Service URLs
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")
RESULTS_API_URL = os.getenv("RESULTS_API_URL", "http://localhost:8080")


async def run_performance_test():
    """Run performance tests"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            logger.info("Starting performance test...")
            
            # Test 1: API response times
            await test_api_response_times(client)
            
            # Test 2: Concurrent job processing
            await test_concurrent_jobs(client)
            
            # Test 3: Results API throughput
            await test_results_throughput(client)
            
            logger.info("Performance test completed! ✅")
            
    except Exception as e:
        logger.error("Performance test failed", error=str(e))
        raise


async def test_api_response_times(client):
    """Test API response times"""
    logger.info("Testing API response times...")
    
    endpoints = [
        ("Health Check", f"{ORCHESTRATOR_URL}/health"),
        ("Results API Health", f"{RESULTS_API_URL}/health"),
        ("System Stats", f"{RESULTS_API_URL}/stats"),
        ("Results List", f"{RESULTS_API_URL}/results?limit=10")
    ]
    
    for endpoint_name, url in endpoints:
        response_times = []
        
        for i in range(5):  # 5 requests per endpoint
            start_time = time.time()
            
            try:
                response = await client.get(url)
                response.raise_for_status()
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to ms
                response_times.append(response_time)
                
            except Exception as e:
                logger.error(f"Request failed for {endpoint_name}", error=str(e))
        
        if response_times:
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            logger.info(f"{endpoint_name} response times", 
                       avg_ms=f"{avg_time:.2f}",
                       min_ms=f"{min_time:.2f}",
                       max_ms=f"{max_time:.2f}")


async def test_concurrent_jobs(client):
    """Test concurrent job processing"""
    logger.info("Testing concurrent job processing...")
    
    job_request = {
        "industry": "test pillows",
        "top_amz": 2,
        "top_ebay": 2,
        "platforms": ["youtube"],
        "recency_days": 30
    }
    
    # Start multiple jobs concurrently
    num_jobs = 3
    start_time = time.time()
    
    tasks = []
    for i in range(num_jobs):
        task = asyncio.create_task(start_and_wait_for_job(client, job_request, f"concurrent-{i}"))
        tasks.append(task)
    
    # Wait for all jobs to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    successful_jobs = sum(1 for result in results if not isinstance(result, Exception))
    
    logger.info("Concurrent job test completed",
               total_jobs=num_jobs,
               successful_jobs=successful_jobs,
               total_time_s=f"{total_time:.2f}",
               avg_time_per_job_s=f"{total_time/num_jobs:.2f}")


async def start_and_wait_for_job(client, job_request, job_suffix):
    """Start a job and wait for completion"""
    try:
        # Modify industry to make it unique
        unique_request = {**job_request, "industry": f"{job_request['industry']}-{job_suffix}"}
        
        # Start job
        response = await client.post(f"{ORCHESTRATOR_URL}/start-job", json=unique_request)
        response.raise_for_status()
        
        job_data = response.json()
        job_id = job_data["job_id"]
        
        # Wait for completion (simplified - just wait fixed time)
        await asyncio.sleep(30)  # Wait 30 seconds
        
        # Check final status
        response = await client.get(f"{ORCHESTRATOR_URL}/status/{job_id}")
        response.raise_for_status()
        
        status_data = response.json()
        return {"job_id": job_id, "status": status_data["phase"]}
        
    except Exception as e:
        logger.error(f"Job {job_suffix} failed", error=str(e))
        raise


async def test_results_throughput(client):
    """Test results API throughput"""
    logger.info("Testing results API throughput...")
    
    # Make multiple concurrent requests to results API
    num_requests = 20
    start_time = time.time()
    
    tasks = []
    for i in range(num_requests):
        task = asyncio.create_task(client.get(f"{RESULTS_API_URL}/results?limit=50"))
        tasks.append(task)
    
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    successful_requests = sum(1 for resp in responses if not isinstance(resp, Exception))
    requests_per_second = successful_requests / total_time
    
    logger.info("Results API throughput test completed",
               total_requests=num_requests,
               successful_requests=successful_requests,
               total_time_s=f"{total_time:.2f}",
               requests_per_second=f"{requests_per_second:.2f}")


if __name__ == "__main__":
    asyncio.run(run_performance_test())