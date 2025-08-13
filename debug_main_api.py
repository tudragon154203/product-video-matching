#!/usr/bin/env python3
import asyncio
import httpx
import json

async def debug_main_api():
    """Debug the main API step by step"""
    try:
        async with httpx.AsyncClient() as client:
            # Test the exact request that's failing
            job_request = {
                "query": "test pillows",
                "top_amz": 1,
                "top_ebay": 1,
                "platforms": ["youtube"],
                "recency_days": 30
            }
            
            print("Making request to main API...")
            print(f"Request: {json.dumps(job_request, indent=2)}")
            
            try:
                response = await client.post(
                    "http://localhost:8888/start-job", 
                    json=job_request,
                    timeout=120
                )
                print(f"Response status: {response.status_code}")
                print(f"Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    print(f"Success response: {response.json()}")
                else:
                    print(f"Error response: {response.text}")
                    
                    # Try to get more details
                    try:
                        error_data = response.json()
                        print(f"Error JSON: {json.dumps(error_data, indent=2)}")
                    except:
                        print("Could not parse error as JSON")
                        
            except httpx.TimeoutException:
                print("Request timed out")
            except Exception as e:
                print(f"Request failed: {e}")
                
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_main_api())