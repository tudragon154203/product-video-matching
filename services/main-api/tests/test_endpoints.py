"""
Test script for the main API service endpoints.
"""
import asyncio
import json
import sys
import os
import httpx

# Add the libs directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs"))

# Add the current directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from config_loader import load_env, MainAPIConfig


async def test_start_job_endpoint():
    """Test the /start-job endpoint."""
    print("Testing /start-job endpoint...")
    
    # Load configuration
    try:
        config: MainAPIConfig = load_env()
        print(f"Loaded config: OLLAMA_HOST={config.ollama_host}")
    except FileNotFoundError:
        print("Config file not found, using default config")
        config = MainAPIConfig(
            ollama_host="http://host.docker.internal:11434",
            model_classify="qwen3:4b-instruct",
            model_generate="qwen3:4b-instruct",
            ollama_timeout=60,
            industry_labels=["fashion","beauty_personal_care","books","electronics","home_garden","sports_outdoors","baby_products","pet_supplies","toys_games","automotive","office_products","business_industrial","collectibles_art","jewelry_watches","other"],
            default_top_amz=20,
            default_top_ebay=20,
            default_platforms=["youtube","bilibili"],
            default_recency_days=30
        )
    
    # Test request
    test_request = {
        "query": "ergonomic office chair",
        "top_amz": 10,
        "top_ebay": 5,
        "platforms": ["youtube"],
        "recency_days": 30
    }
    
    # Make request to the /start-job endpoint
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/start-job",
                json=test_request,
                timeout=120
            )
            
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                if "job_id" in data and data["status"] == "started":
                    print("Test passed!")
                    return True
                else:
                    print("Test failed: Unexpected response format")
                    return False
            else:
                print(f"Test failed: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error: {response.text}")
                return False
                
    except Exception as e:
        print(f"Test failed with exception: {e}")
        return False


async def test_health_endpoint():
    """Test the /health endpoint."""
    print("Testing /health endpoint...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8000/health",
                timeout=30
            )
            
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                if data.get("status") == "healthy" and data.get("service") == "main-api":
                    print("Test passed!")
                    return True
                else:
                    print("Test failed: Unexpected response format")
                    return False
            else:
                print(f"Test failed: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error: {response.text}")
                return False
                
    except Exception as e:
        print(f"Test failed with exception: {e}")
        return False


async def main():
    """Run all tests."""
    print("Running API endpoint tests...")
    
    # Test health endpoint
    health_passed = await test_health_endpoint()
    print()
    
    # Test start-job endpoint
    start_job_passed = await test_start_job_endpoint()
    print()
    
    if health_passed and start_job_passed:
        print("All tests passed!")
        return True
    else:
        print("Some tests failed!")
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)