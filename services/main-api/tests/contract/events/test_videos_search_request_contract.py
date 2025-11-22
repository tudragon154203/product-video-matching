"""
Contract tests for videos_search_request event published by main-api.
Ensures the event adheres to libs/contracts/contracts/schemas/videos_search_request.json
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Add libs to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'libs'))

from contracts.validator import validator
from services.job.job_initializer import JobInitializer
from models.schemas import StartJobRequest

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_videos_search_request_contract_compliance():
    """Test that videos_search_request event published by main-api adheres to the contract schema."""
    
    # Mock dependencies
    mock_db_handler = MagicMock()
    mock_db_handler.store_job = AsyncMock()
    
    mock_broker_handler = MagicMock()
    mock_broker_handler.publish_product_collection_request = AsyncMock()
    mock_broker_handler.publish_video_search_request = AsyncMock()
    
    mock_llm_service = MagicMock()
    mock_llm_service.call_llm = AsyncMock()
    
    # Mock LLM responses
    mock_llm_service.call_llm.side_effect = [
        {"response": "electronics"},  # classify response
        {"response": '{"product": {"en": ["wireless mouse", "gaming mouse"]}, "video": {"vi": ["chuột không dây"], "zh": ["无线鼠标"]}}'}  # generate response
    ]
    
    mock_prompt_service = MagicMock()
    mock_prompt_service.build_cls_prompt = MagicMock(return_value="classify prompt")
    mock_prompt_service.build_gen_prompt = MagicMock(return_value="generate prompt")
    mock_prompt_service.normalize_queries = MagicMock(return_value={
        "product": {"en": ["wireless mouse", "gaming mouse"]},
        "video": {"vi": ["chuột không dây"], "zh": ["无线鼠标"]}
    })
    mock_prompt_service.route_video_queries = MagicMock(return_value={
        "vi": ["chuột không dây"],
        "zh": ["无线鼠标"]
    })
    
    # Create job initializer
    job_initializer = JobInitializer(
        db_handler=mock_db_handler,
        broker_handler=mock_broker_handler,
        llm_service=mock_llm_service,
        prompt_service=mock_prompt_service
    )
    
    # Create test request
    test_request = StartJobRequest(
        query="wireless mouse",
        top_amz=10,
        top_ebay=5,
        platforms=["youtube", "bilibili"],
        recency_days=30
    )
    
    # Initialize job
    job_id = "test-job-123"
    await job_initializer.initialize_job(job_id, test_request)
    
    # Verify publish_video_search_request was called
    assert mock_broker_handler.publish_video_search_request.called
    
    # Extract the event data that would be published
    call_args = mock_broker_handler.publish_video_search_request.call_args
    published_event = {
        "job_id": call_args[0][0],
        "industry": call_args[0][1],
        "queries": call_args[0][2],
        "platforms": call_args[0][3],
        "recency_days": call_args[0][4]
    }
    
    # Validate against schema
    is_valid = validator.validate_event("videos_search_request", published_event)
    assert is_valid, "videos_search_request event should be valid according to schema"
    
    # Additional field validations
    assert published_event["job_id"] == job_id
    assert published_event["industry"] == "electronics"
    assert isinstance(published_event["queries"], dict)
    assert "vi" in published_event["queries"]
    assert "zh" in published_event["queries"]
    assert isinstance(published_event["queries"]["vi"], list)
    assert isinstance(published_event["queries"]["zh"], list)
    assert published_event["platforms"] == ["youtube", "bilibili"]
    assert published_event["recency_days"] == 30


@pytest.mark.asyncio
async def test_videos_search_request_required_fields():
    """Test that all required fields are present in videos_search_request event."""
    
    # Get the schema
    schema = validator.get_schema("videos_search_request")
    required_fields = schema.get("required", [])
    
    # Expected required fields based on the schema
    expected_required = ["job_id", "industry", "queries", "platforms", "recency_days"]
    
    assert set(required_fields) == set(expected_required), \
        f"Schema required fields mismatch. Expected: {expected_required}, Got: {required_fields}"


@pytest.mark.asyncio
async def test_videos_search_request_queries_structure():
    """Test that queries field has the correct structure with at least one language."""
    
    # Get the schema
    schema = validator.get_schema("videos_search_request")
    queries_schema = schema["properties"]["queries"]
    
    # Verify queries is an object
    assert queries_schema["type"] == "object"
    
    # Verify minProperties is set to 1
    assert queries_schema.get("minProperties") == 1, "At least one language should be required"
    
    # Verify vi and zh are NOT in required (they're optional)
    queries_required = queries_schema.get("required", [])
    assert "vi" not in queries_required, "vi should be optional"
    assert "zh" not in queries_required, "zh should be optional"
    
    # Verify vi and zh properties exist and are arrays of strings
    assert queries_schema["properties"]["vi"]["type"] == "array"
    assert queries_schema["properties"]["vi"]["items"]["type"] == "string"
    assert queries_schema["properties"]["zh"]["type"] == "array"
    assert queries_schema["properties"]["zh"]["items"]["type"] == "string"


@pytest.mark.asyncio
async def test_videos_search_request_platforms_enum():
    """Test that platforms field has correct enum values."""
    
    # Get the schema
    schema = validator.get_schema("videos_search_request")
    platforms_schema = schema["properties"]["platforms"]
    
    # Verify platforms is an array
    assert platforms_schema["type"] == "array"
    
    # Verify enum values
    expected_platforms = ["youtube", "bilibili", "douyin", "tiktok"]
    actual_enum = platforms_schema["items"]["enum"]
    
    assert set(actual_enum) == set(expected_platforms), \
        f"Platform enum mismatch. Expected: {expected_platforms}, Got: {actual_enum}"


@pytest.mark.asyncio
async def test_videos_search_request_recency_days_minimum():
    """Test that recency_days has minimum value constraint."""
    
    # Get the schema
    schema = validator.get_schema("videos_search_request")
    recency_schema = schema["properties"]["recency_days"]
    
    # Verify it's an integer with minimum 1
    assert recency_schema["type"] == "integer"
    assert recency_schema["minimum"] == 1


@pytest.mark.asyncio
async def test_videos_search_request_single_language():
    """Test that videos_search_request works with only one language."""
    
    # Test with only vi
    event_vi_only = {
        "job_id": "test-job-vi",
        "industry": "electronics",
        "queries": {"vi": ["chuột không dây"]},
        "platforms": ["youtube"],
        "recency_days": 30
    }
    
    is_valid = validator.validate_event("videos_search_request", event_vi_only)
    assert is_valid, "Event with only vi should be valid"
    
    # Test with only zh
    event_zh_only = {
        "job_id": "test-job-zh",
        "industry": "electronics",
        "queries": {"zh": ["无线鼠标"]},
        "platforms": ["bilibili"],
        "recency_days": 30
    }
    
    is_valid = validator.validate_event("videos_search_request", event_zh_only)
    assert is_valid, "Event with only zh should be valid"
    
    # Test with empty queries (should fail)
    event_empty = {
        "job_id": "test-job-empty",
        "industry": "electronics",
        "queries": {},
        "platforms": ["youtube"],
        "recency_days": 30
    }
    
    try:
        validator.validate_event("videos_search_request", event_empty)
        assert False, "Event with empty queries should fail validation"
    except Exception:
        # Expected to fail
        pass
