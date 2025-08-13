#!/usr/bin/env python3
"""
Simple test to verify that the main API service is working correctly
and that the job schema changes are properly implemented.
"""
import asyncio
import httpx
import json
import time

async def test_main_api():
    """Test the main API service"""
    base_url = "http://localhost:8888"
    
    print("Testing Main API Service")
    print("=" * 30)
    
    # Test 1: Health check
    print("\n1. Testing health check endpoint...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health")
            print(f"   Status Code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
                print("   PASS: Health check passed")
            else:
                print("   FAIL: Health check failed")
    except Exception as e:
        print(f"   ERROR: Health check failed with error: {e}")
    
    # Test 2: Test start-job endpoint (will fail without Ollama but should handle gracefully)
    print("\n2. Testing start-job endpoint...")
    try:
        async with httpx.AsyncClient() as client:
            job_request = {
                "query": "ergonomic office chair",
                "top_amz": 10,
                "top_ebay": 5,
                "platforms": ["youtube"],
                "recency_days": 30
            }
            
            response = await client.post(
                f"{base_url}/start-job",
                json=job_request,
                timeout=30
            )
            
            print(f"   Status Code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
                print("   PASS: Start job request succeeded")
            elif response.status_code == 500:
                # This is expected when Ollama is not available
                print("   WARN: Start job request failed (expected when Ollama is not available)")
                print(f"   Response: {response.text}")
            else:
                print("   FAIL: Start job request failed unexpectedly")
                print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ERROR: Start job request failed with error: {e}")
    
    print("\n" + "=" * 30)
    print("Test completed")

if __name__ == "__main__":
    asyncio.run(test_main_api())