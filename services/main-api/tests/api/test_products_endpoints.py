"""
Test script for the main API service product endpoints.
"""
import asyncio
import json
import sys
import httpx
import pytest

from config_loader import config as MainAPIConfig


@pytest.mark.asyncio
async def test_get_job_products_success():
    """Test the /jobs/{job_id}/products endpoint with a valid job ID."""
    print("Testing /jobs/{job_id}/products endpoint with valid job ID...")
    
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
                print(f"✗ Get job products test failed: Could not start job - HTTP {start_response.status_code}")
                assert False, f"Could not start job - HTTP {start_response.status_code}"
                
            start_data = start_response.json()
            job_id = start_data.get("job_id")
            
            if not job_id:
                print("✗ Get job products test failed: No job_id in start job response")
                assert False, "No job_id in start job response"
                
            print(f"Started job with ID: {job_id}")
            
            # Now test the products endpoint
            response = await client.get(
                f"http://localhost:8888/jobs/{job_id}/products",
                timeout=30
            )
            
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                # Validate response structure
                required_fields = ["items", "total", "limit", "offset"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    print(f"✗ Get job products test failed: Missing fields: {missing_fields}")
                    assert False, f"Missing fields: {missing_fields}"
                
                # Validate data types
                assert isinstance(data["items"], list), "items should be a list"
                assert isinstance(data["total"], int), "total should be an integer"
                assert isinstance(data["limit"], int), "limit should be an integer"
                assert isinstance(data["offset"], int), "offset should be an integer"
                
                # Validate pagination values
                assert data["limit"] >= 0, "limit should be non-negative"
                assert data["offset"] >= 0, "offset should be non-negative"
                assert data["total"] >= 0, "total should be non-negative"
                
                # If there are items, validate their structure
                if len(data["items"]) > 0:
                    item = data["items"][0]
                    required_item_fields = ["product_id", "src", "asin_or_itemid", "title", "brand", "url", "image_count", "created_at"]
                    missing_item_fields = [field for field in required_item_fields if field not in item]
                    
                    if missing_item_fields:
                        print(f"✗ Get job products test failed: Missing item fields: {missing_item_fields}")
                        assert False, f"Missing item fields: {missing_item_fields}"
                    
                    # Validate item field types
                    assert isinstance(item["product_id"], str), "product_id should be string"
                    assert isinstance(item["src"], str), "src should be string"
                    assert isinstance(item["title"], str), "title should be string"
                    assert isinstance(item["image_count"], int), "image_count should be integer"
                    assert item["image_count"] >= 0, "image_count should be non-negative"
                
                print("✓ Get job products endpoint test passed")
                assert True
            else:
                print(f"✗ Get job products test failed: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error: {response.text}")
                assert False, f"HTTP {response.status_code}"
                
    except Exception as e:
        print(f"✗ Get job products test failed: {e}")
        assert False, str(e)


@pytest.mark.asyncio
async def test_get_job_products_invalid_job():
    """Test the /jobs/{job_id}/products endpoint with invalid job ID."""
    print("Testing /jobs/{job_id}/products endpoint with invalid job ID...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8888/jobs/invalid-job-id/products",
                timeout=30
            )
            
            print(f"Status code: {response.status_code}")
            
            # For invalid job IDs, we expect either:
            # 1. A 200 response with empty items (as products might not be found for unknown job)
            # 2. A 404 response indicating job not found
            # We should NOT get a 500 error
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                # Should return valid structure even for unknown job
                required_fields = ["items", "total", "limit", "offset"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    print(f"✗ Get job products test for invalid job failed: Missing fields: {missing_fields}")
                    assert False, f"Missing fields: {missing_fields}"
                
                # Should have empty items or valid structure
                assert isinstance(data["items"], list), "items should be a list"
                assert isinstance(data["total"], int), "total should be an integer"
                assert data["total"] >= 0, "total should be non-negative"
                
                print("✓ Get job products endpoint test for invalid job passed")
                assert True
            elif response.status_code == 404:
                # 404 is also acceptable for a non-existent job
                print("✓ Get job products endpoint test for invalid job passed (404 response)")
                assert True
            else:
                print(f"✗ Get job products test for invalid job failed: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error: {response.text}")
                assert False, f"HTTP {response.status_code} - Expected 200 or 404 for invalid job ID"
                
    except Exception as e:
        print(f"✗ Get job products test for invalid job failed: {e}")
        assert False, str(e)


@pytest.mark.asyncio
async def test_get_job_products_with_filters():
    """Test the /jobs/{job_id}/products endpoint with query parameters."""
    print("Testing /jobs/{job_id}/products endpoint with query parameters...")
    
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
                print(f"✗ Get job products with filters test failed: Could not start job - HTTP {start_response.status_code}")
                assert False, f"Could not start job - HTTP {start_response.status_code}"
                
            start_data = start_response.json()
            job_id = start_data.get("job_id")
            
            if not job_id:
                print("✗ Get job products with filters test failed: No job_id in start job response")
                assert False, "No job_id in start job response"
                
            print(f"Started job with ID: {job_id}")
            
            # Test with limit parameter
            response = await client.get(
                f"http://localhost:8888/jobs/{job_id}/products?limit=5",
                timeout=30
            )
            
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response with limit=5: {json.dumps(data, indent=2)}")
                
                # Validate response structure
                assert "items" in data, "Response should contain items"
                assert "limit" in data, "Response should contain limit"
                assert data["limit"] == 5, f"Expected limit=5, got {data['limit']}"
                
                print("✓ Get job products endpoint test with filters passed")
                assert True
            else:
                print(f"✗ Get job products with filters test failed: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error: {response.text}")
                assert False, f"HTTP {response.status_code}"
                
    except Exception as e:
        print(f"✗ Get job products with filters test failed: {e}")
        assert False, str(e)