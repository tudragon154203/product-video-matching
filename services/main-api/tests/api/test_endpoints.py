"""
Test script for the main API service endpoints.
"""
import asyncio
import json


from config_loader import config as MainAPIConfig


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


async def main():
    """Run all tests."""
    print("Running main API service tests...\n")
    
    # Test health endpoint
    health_passed = await test_health_endpoint()
    print()
    
    # Test start job endpoint
    start_job_passed = await test_start_job_endpoint()
    print()
    
    # Print summary
    print("Test Summary:")
    print(f"  Health endpoint: {'PASS' if health_passed else 'FAIL'}")
    print(f"  Start job endpoint: {'PASS' if start_job_passed else 'FAIL'}")
    
    if health_passed and start_job_passed:
        print("\n✓ All tests passed!")
        return True
    else:
        print("\n✗ Some tests failed!")
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)