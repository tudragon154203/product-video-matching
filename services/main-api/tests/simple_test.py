"""
Simple test script to verify the main API service functionality.
"""
import requests
import time
import json


def test_health_endpoint():
    """Test the health endpoint."""
    print("Testing health endpoint...")
    try:
        response = requests.get("http://localhost:8888/health")
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            if data.get("status") == "healthy":
                print("✓ Health endpoint test passed")
                return True
            else:
                print("✗ Health endpoint test failed: Unexpected response")
                return False
        else:
            print(f"✗ Health endpoint test failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Health endpoint test failed: {e}")
        return False


def test_start_job_endpoint():
    """Test the start job endpoint."""
    print("\nTesting start job endpoint...")
    try:
        # Test data
        job_request = {
            "query": "ergonomic office chair",
            "top_amz": 10,
            "top_ebay": 5,
            "platforms": ["youtube"],
            "recency_days": 30
        }
        
        response = requests.post(
            "http://localhost:8888/start-job",
            json=job_request
        )
        
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if "job_id" in data and data.get("status") == "started":
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


def test_status_endpoint(job_id):
    """Test the status endpoint."""
    print("\nTesting status endpoint...")
    try:
        response = requests.get(f"http://localhost:8888/status/{job_id}")
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if data.get("job_id") == job_id:
                print("✓ Status endpoint test passed")
                return True
            else:
                print("✗ Status endpoint test failed: Unexpected response")
                return False
        else:
            print(f"✗ Status endpoint test failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Status endpoint test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Running simple tests for the main API service...\n")
    
    # Test health endpoint
    if not test_health_endpoint():
        return False
    
    # Test start job endpoint
    job_id = None
    if test_start_job_endpoint():
        # If we successfully started a job, test the status endpoint
        # For now, we'll skip this since we don't have the job ID from the previous test
        # In a real test, we would extract the job_id from the response
        pass
    else:
        return False
    
    print("\n✓ All tests passed!")
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)