import requests
import json
import time
import os

BASE_URL = "http://localhost:8000"

def test_health_endpoint():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    print("✓ Health endpoint test passed")
    return True

def test_start_job_endpoint():
    job_request = {
        "query": "red dress",
        "industry": "fashion",
        "video_urls": [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        ],
        "image_urls": [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg"
        ]
    }
    response = requests.post(f"{BASE_URL}/jobs", json=job_request)
    assert response.status_code == 200
    job_response = response.json()
    assert "job_id" in job_response
    print(f"✓ Start job endpoint test passed. Job ID: {job_response['job_id']}")
    return job_response["job_id"]

def _test_status_endpoint(job_id: str):
    print(f"Checking status for Job ID: {job_id}")
    retries = 10
    while retries > 0:
        response = requests.get(f"{BASE_URL}/jobs/{job_id}/status")
        assert response.status_code == 200
        status_data = response.json()
        print(f"Current status: {status_data.get('phase')}")
        if status_data.get("phase") == "completed":
            print("✓ Status endpoint test passed. Job completed.")
            return
        time.sleep(5)
        retries -= 1
    print("✗ Status endpoint test failed: Job did not complete in time.")
    assert False, "Job did not complete in time."

def main():
    # Ensure the main API is running before starting tests
    try:
        requests.get(f"{BASE_URL}/health")
        print("Main API is running.")
    except requests.exceptions.ConnectionError:
        print("Error: Main API is not running. Please start it using 'docker compose up' or 'python main.py'.")
        return

    # Run tests in sequence
    test_health_endpoint()
    job_id = test_start_job_endpoint()
    if job_id:
        _test_status_endpoint(job_id)

if __name__ == "__main__":
    main()