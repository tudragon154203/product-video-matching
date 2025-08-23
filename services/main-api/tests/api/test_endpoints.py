"""
Test script for the main API service endpoints.
"""
import asyncio
import json
import sys
import httpx
import pytest

from config_loader import config as MainAPIConfig
from .test_video_endpoints import (
    test_get_job_videos_success,
    test_get_job_videos_not_found,
    test_get_job_videos_with_query_params,
    test_get_video_frames_success,
    test_get_video_frames_job_not_found,
    test_get_video_frames_video_not_found,
    test_get_video_frames_video_not_belong_to_job,
    test_get_video_frames_with_query_params
)


async def test_start_job_endpoint():
    """Test the /start-job endpoint."""
    print("Testing /start-job endpoint...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test data
            test_data = {
                "query": "ergonomic office chair",
                "top_amz": 20,
                "top_ebay": 20,
                "platforms": ["youtube", "bilibili"],
                "recency_days": 30
            }
            
            response = await client.post(
                "http://localhost:8888/start-job",
                json=test_data,
                timeout=30
            )
            
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                if "job_id" in data and data["status"] == "started":
                    print("✓ Start job endpoint test passed")
                    return True
                else:
                    print("✗ Start job endpoint test failed: Unexpected response")
                    return False
            else:
                print(f"✗ Start job endpoint test failed: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error: {response.text}")
                return False
                
    except Exception as e:
        print(f"✗ Start job endpoint test failed: {e}")
        return False


async def test_health_endpoint():
    """Test the /health endpoint."""
    print("Testing /health endpoint...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8888/health",
                timeout=30
            )
            
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                if data.get("status") == "healthy" and data.get("service") == "main-api":
                    print("✓ Health endpoint test passed")
                    return True
                else:
                    print("✗ Health endpoint test failed: Unexpected response")
                    return False
            else:
                print(f"✗ Health endpoint test failed: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error: {response.text}")
                return False
                
    except Exception as e:
        print(f"✗ Health endpoint test failed: {e}")
        return False


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
                return False
                
            start_data = start_response.json()
            job_id = start_data.get("job_id")
            
            if not job_id:
                print("✗ Status endpoint test failed: No job_id in start job response")
                return False
                
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
                    return False
                
                # Validate counts structure
                required_counts = ["products", "videos", "images", "frames"]
                missing_counts = [count for count in required_counts if count not in data["counts"]]
                
                if missing_counts:
                    print(f"✗ Status endpoint test failed: Missing counts: {missing_counts}")
                    return False
                
                # Validate data types
                if not isinstance(data["job_id"], str):
                    print("✗ Status endpoint test failed: job_id should be string")
                    return False
                    
                if not isinstance(data["phase"], str):
                    print("✗ Status endpoint test failed: phase should be string")
                    return False
                    
                if not isinstance(data["percent"], (int, float)) or not (0 <= data["percent"] <= 100):
                    print("✗ Status endpoint test failed: percent should be number between 0-100")
                    return False
                    
                if not isinstance(data["counts"], dict):
                    print("✗ Status endpoint test failed: counts should be dict")
                    return False
                    
                # Validate counts are non-negative integers
                for count_type, count_value in data["counts"].items():
                    if not isinstance(count_value, int) or count_value < 0:
                        print(f"✗ Status endpoint test failed: {count_type} count should be non-negative integer")
                        return False
                
                print("✓ Status endpoint test passed")
                return True
            else:
                print(f"✗ Status endpoint test failed: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error: {response.text}")
                return False
                
    except Exception as e:
        print(f"✗ Status endpoint test failed: {e}")
        return False


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
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                # Should return default values for unknown job
                if (data.get("job_id") == "invalid-job-id" and
                    data.get("phase") == "unknown" and
                    data.get("percent") == 0.0 and
                    data.get("counts") == {"products": 0, "videos": 0, "images": 0, "frames": 0}):
                    print("✓ Status endpoint test for invalid job passed")
                    return True
                else:
                    print("✗ Status endpoint test for invalid job failed: Unexpected response for unknown job")
                    return False
            else:
                print(f"✗ Status endpoint test for invalid job failed: HTTP {response.status_code}")
                return False
                
    except Exception as e:
        print(f"✗ Status endpoint test for invalid job failed: {e}")
        return False


if __name__ == "__main__":
    # To run these tests, you need to have pytest and httpx installed:
    # pip install pytest httpx pytest-asyncio
    # And ensure your main-api service is running on http://localhost:8888
    
    async def run_all_tests():
        results = []
        results.append(await test_start_job_endpoint())
        results.append(await test_health_endpoint())
        results.append(await test_status_endpoint())
        results.append(await test_status_endpoint_invalid_job())
        
        # Run video endpoint tests
        # The mock_db_instances fixture is handled by pytest when run with 'pytest' command.
        # For direct execution via asyncio.run, you would need to manually set up mocks.
        # Here we assume pytest will manage the fixture injection for these tests.
        try:
            # We're passing a dummy argument to the test functions that expect mock_db_instances
            # because we're running them outside of pytest's fixture injection.
            # When pytest runs, it will inject the actual fixture.
            results.append(await test_get_job_videos_success(None))
            results.append(await test_get_job_videos_not_found(None))
            results.append(await test_get_job_videos_with_query_params(None))
            results.append(await test_get_video_frames_success(None))
            results.append(await test_get_video_frames_job_not_found(None))
            results.append(await test_get_video_frames_video_not_found(None))
            results.append(await test_get_video_frames_video_not_belong_to_job(None))
            results.append(await test_get_video_frames_with_query_params(None))
        except Exception as e:
            print(f"Error running video endpoint tests: {e}")
            results.append(False)
        
        if all(results):
            print("\nAll tests passed!")
        else:
            print("\nSome tests failed.")
            sys.exit(1)

    asyncio.run(run_all_tests())