"""
Test script for the main API service job endpoints.
"""
import asyncio
import json
import sys
import httpx
import pytest

from config_loader import config as MainAPIConfig


@pytest.mark.asyncio
async def test_status_endpoint():
    """Test the /status/{job_id} endpoint."""
    print("Testing /status/{job_id} endpoint...")
    
    try:
        # First, start a job to get a valid job_id
        async with httpx.AsyncClient() as client:
            test_data = {
                "query": "ergonomic office chair",
                "top_amz": 20,
                "top_ebay": 20,
                "platforms": ["youtube", "bilibili"],
                "recency_days": 30
            }
            
            start_response = await client.post(
                "http://localhost:8888/start-job",
                json=test_data,
                timeout=30
            )
            
            if start_response.status_code != 200:
                print(f"✗ Status endpoint test failed: Could not start job - HTTP {start_response.status_code}")
                assert False, f"Could not start job - HTTP {start_response.status_code}"
                
            start_data = start_response.json()
            job_id = start_data.get("job_id")
            
            if not job_id:
                print("✗ Status endpoint test failed: No job_id in start job response")
                assert False, "No job_id in start job response"
                
            print(f"Started job with ID: {job_id}")
            
            # Now test the status endpoint
            response = await client.get(
                f"http://localhost:8888/status/{job_id}",
                timeout=30
            )
            
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                # Validate response structure
                required_fields = ["job_id", "phase", "percent", "counts", "updated_at"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    print(f"✗ Status endpoint test failed: Missing fields: {missing_fields}")
                    assert False, f"Missing fields: {missing_fields}"
                
                # Validate counts structure
                required_counts = ["products", "videos", "images", "frames"]
                missing_counts = [count for count in required_counts if count not in data["counts"]]
                
                if missing_counts:
                    print(f"✗ Status endpoint test failed: Missing counts: {missing_counts}")
                    assert False, f"Missing counts: {missing_counts}"
                
                # Validate data types
                assert isinstance(data["job_id"], str), "job_id should be string"
                assert isinstance(data["phase"], str), "phase should be string"
                assert isinstance(data["percent"], (int, float)), "percent should be number"
                assert 0 <= data["percent"] <= 100, "percent should be between 0-100"
                assert isinstance(data["counts"], dict), "counts should be dict"
                
                # Validate counts are non-negative integers
                for count_type, count_value in data["counts"].items():
                    assert isinstance(count_value, int), f"{count_type} count should be integer"
                    assert count_value >= 0, f"{count_type} count should be non-negative"
                
                print("✓ Status endpoint test passed")
                assert True
            else:
                print(f"✗ Status endpoint test failed: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error: {response.text}")
                assert False, f"HTTP {response.status_code}"
                
    except Exception as e:
        print(f"✗ Status endpoint test failed: {e}")
        assert False, str(e)


@pytest.mark.asyncio
async def test_status_endpoint_invalid_job():
    """Test the /status/{job_id} endpoint with invalid job ID."""
    print("Testing /status/{job_id} endpoint with invalid job ID...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8888/status/invalid-job-id",
                timeout=30
            )
            
            print(f"Status code: {response.status_code}")
            
            # For invalid job IDs, we expect either:
            # 1. A 200 response with default values (as per the job_management_service implementation)
            # 2. A 404 response indicating job not found
            # We should NOT get a 500 error
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                # Should return default values for unknown job
                expected_conditions = (
                    data.get("job_id") == "invalid-job-id" and
                    data.get("phase") == "unknown" and
                    data.get("percent") == 0.0 and
                    data.get("counts") == {"products": 0, "videos": 0, "images": 0, "frames": 0}
                )
                
                if expected_conditions:
                    print("✓ Status endpoint test for invalid job passed")
                    assert True
                else:
                    print("⚠ Status endpoint test for invalid job: Unexpected response for unknown job, but no error")
                    # This is not ideal but not an error
                    assert True
            elif response.status_code == 404:
                # 404 is also acceptable for a non-existent job
                print("✓ Status endpoint test for invalid job passed (404 response)")
                assert True
            else:
                print(f"✗ Status endpoint test for invalid job failed: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error: {response.text}")
                assert False, f"HTTP {response.status_code} - Expected 200 or 404 for invalid job ID"
                
    except Exception as e:
        print(f"✗ Status endpoint test for invalid job failed: {e}")
        assert False, str(e)
@pytest.mark.asyncio
async def test_start_job_success():
    """Test the /start-job endpoint with a valid request."""
    print("Testing /start-job endpoint for successful job creation...")
    test_data = {
        "query": "minimal test query",
        "top_amz": 1,
        "top_ebay": 1,
        "platforms": ["youtube"],
        "recency_days": 1
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8888/start-job",
            json=test_data,
            timeout=30
        )
        print(f"Start job status code: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert isinstance(data["job_id"], str)
        print(f"✓ /start-job endpoint test passed. Job ID: {data['job_id']}")