"""
Integration test for start-job endpoint event publishing.
Tests that the API publishes schematically correct events to RabbitMQ.
"""
import pytest
import asyncio
import sys
from pathlib import Path

# Ensure libs path is available (conftest should handle this but being explicit)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIBS_PATH = PROJECT_ROOT / "libs"
CONTRACTS_PATH = LIBS_PATH / "contracts"

for path in [LIBS_PATH, CONTRACTS_PATH]:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from contracts.validator import EventValidator

# Create validator instance
validator = EventValidator()

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_start_job_publishes_valid_product_and_video_events(
    main_api_url,
    message_spy,
    clean_database,
    http_client
):
    """
    Integration test: POST /start-job publishes valid product collection
    and video search request events that conform to their schemas.
    """
    # Create spy queues for the events we want to capture
    product_queue = await message_spy.create_spy_queue("products.collect.request")
    video_queue = await message_spy.create_spy_queue("videos.search.request")
    
    # Start consuming from both queues
    await message_spy.start_consuming(product_queue)
    await message_spy.start_consuming(video_queue)
    
    # Make the API request
    job_request = {
        "query": "wireless mouse",
        "top_amz": 10,
        "top_ebay": 5,
        "platforms": ["youtube", "bilibili"],
        "recency_days": 365
    }
    
    response = await http_client.post(f"{main_api_url}/start-job", json=job_request)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    job_data = response.json()
    job_id = job_data["job_id"]
    assert job_id is not None
    
    # Wait for events to be published
    await asyncio.sleep(3)
    
    # Get captured messages
    product_messages = message_spy.get_captured_messages(product_queue)
    video_messages = message_spy.get_captured_messages(video_queue)
    
    # Verify we got both events
    assert len(product_messages) >= 1, "Should have published product collection request"
    assert len(video_messages) >= 1, "Should have published video search request"
    
    # Find the events for our job (messages are wrapped with metadata)
    product_event = None
    for msg in product_messages:
        event_data = msg.get("event_data", {})
        if event_data.get("job_id") == job_id:
            product_event = event_data
            break
    
    video_event = None
    for msg in video_messages:
        event_data = msg.get("event_data", {})
        if event_data.get("job_id") == job_id:
            video_event = event_data
            break
    
    assert product_event is not None, f"Product event not found for job {job_id}"
    assert video_event is not None, f"Video event not found for job {job_id}"
    
    # Validate product collection request schema
    is_valid_product = validator.validate_event("products_collect_request", product_event)
    assert is_valid_product, "Product collection request should conform to schema"
    
    # Verify product event structure
    assert product_event["job_id"] == job_id
    assert product_event["top_amz"] == 10
    assert product_event["top_ebay"] == 5
    assert "queries" in product_event
    assert "en" in product_event["queries"]
    assert len(product_event["queries"]["en"]) > 0
    
    # Validate video search request schema
    is_valid_video = validator.validate_event("videos_search_request", video_event)
    assert is_valid_video, "Video search request should conform to schema"
    
    # Verify video event structure
    assert video_event["job_id"] == job_id
    assert "industry" in video_event
    assert video_event["platforms"] == ["youtube", "bilibili"]
    assert video_event["recency_days"] == 365
    assert "queries" in video_event
    assert len(video_event["queries"]) >= 1, "Should have at least one language"


@pytest.mark.asyncio
async def test_start_job_product_event_respects_limits(
    main_api_url,
    message_spy,
    clean_database,
    http_client
):
    """
    Integration test: Product collection request respects top_amz and top_ebay limits.
    """
    # Create and start consuming from product queue
    product_queue = await message_spy.create_spy_queue("products.collect.request")
    await message_spy.start_consuming(product_queue)
    
    job_request = {
        "query": "laptop stand",
        "top_amz": 50,
        "top_ebay": 25,
        "platforms": ["youtube"],
        "recency_days": 60
    }
    
    response = await http_client.post(f"{main_api_url}/start-job", json=job_request)
    assert response.status_code == 200
    
    job_id = response.json()["job_id"]
    
    # Wait for event
    await asyncio.sleep(3)
    
    product_messages = message_spy.get_captured_messages(product_queue)
    product_event = None
    for msg in product_messages:
        event_data = msg.get("event_data", {})
        if event_data.get("job_id") == job_id:
            product_event = event_data
            break
    
    assert product_event is not None
    
    # Validate schema
    is_valid = validator.validate_event("products_collect_request", product_event)
    assert is_valid, "Product event should be valid"
    
    # Verify limits are respected (0-100 range per schema)
    assert 0 <= product_event["top_amz"] <= 100
    assert 0 <= product_event["top_ebay"] <= 100
    assert product_event["top_amz"] == 50
    assert product_event["top_ebay"] == 25
