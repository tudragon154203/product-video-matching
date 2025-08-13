#!/usr/bin/env python3
import httpx
import asyncio
import json

async def test_simple_api():
    """Test the API with a simple request"""
    try:
        async with httpx.AsyncClient() as client:
            # Test health first
            print("Testing health endpoint...")
            response = await client.get("http://localhost:8888/health")
            print(f"Health status: {response.status_code}")
            print(f"Health response: {response.json()}")
            
            # Test start-job
            print("\nTesting start-job endpoint...")
            job_request = {
                "query": "test pillows",
                "top_amz": 1,
                "top_ebay": 1,
                "platforms": ["youtube"],
                "recency_days": 30
            }
            
            try:
                response = await client.post(
                    "http://localhost:8888/start-job", 
                    json=job_request,
                    timeout=120  # Longer timeout
                )
                print(f"Start-job status: {response.status_code}")
                if response.status_code == 200:
                    print(f"Start-job response: {response.json()}")
                else:
                    print(f"Start-job error: {response.text}")
            except Exception as e:
                print(f"Start-job request failed: {e}")
                
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_api())