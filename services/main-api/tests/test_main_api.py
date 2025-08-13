import os
import pytest
from unittest.mock import patch, AsyncMock, Mock
from fastapi import HTTPException
import httpx

# Add project root to PYTHONPATH for local imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config_loader import config
from main import (
    build_cls_prompt,
    build_gen_prompt,
    normalize_queries,
    route_video_queries,
    StartJobRequest,
    call_ollama
)

def test_build_cls_prompt():
    """Test the build_cls_prompt function."""
    test_query = "ergonomic office chair"
    prompt = build_cls_prompt(test_query, config.INDUSTRY_LABELS)
    assert "ergonomic office chair" in prompt
    assert "Classify this query into one industry label" in prompt
    assert "Labels" in prompt
    assert "Output only the label name" in prompt

def test_build_gen_prompt():
    """Test the build_gen_prompt function."""
    test_query = "ergonomic office chair"
    industry = "office_products"
    prompt = build_gen_prompt(test_query, industry)
    assert "ergonomic office chair" in prompt
    assert "office_products" in prompt
    assert "Generate search queries" in prompt

def test_normalize_queries():
    """Test the normalize_queries function."""
    # Test with valid input
    queries = {
        "product": {
            "en": ["query 1", "query 2"]
        },
        "video": {
            "vi": ["truy vấn 1", "truy vấn 2"],
            "zh": ["查询 1", "查询 2"]
        }
    }
    normalized = normalize_queries(queries)
    assert normalized == queries

    # Test with missing product queries
    queries_no_product = {
        "video": {
            "vi": ["truy vấn 1"]
        }
    }
    normalized_no_product = normalize_queries(queries_no_product)
    assert normalized_no_product == {
        "product": {"en": []},
        "video": {"vi": ["truy vấn 1", "truy vấn 1"], "zh": []}
    }

    # Test with empty queries
    queries_empty = {}
    normalized_empty = normalize_queries(queries_empty)
    assert normalized_empty == {
        "product": {"en": []},
        "video": {"vi": [], "zh": []}
    }

def test_route_video_queries():
    """Test the route_video_queries function."""
    queries = {
        "video": {
            "vi": ["truy vấn 1", "truy vấn 2"],
            "zh": ["查询 1", "查询 2"]
        }
    }
    
    # Test with YouTube platform (should get vi queries)
    routed_youtube = route_video_queries(queries, ["youtube"])
    assert "vi" in routed_youtube
    assert routed_youtube["vi"] == queries["video"]["vi"]
    assert "zh" not in routed_youtube
    
    # Test with Bilibili platform (should get zh queries)
    routed_bilibili = route_video_queries(queries, ["bilibili"])
    assert "zh" in routed_bilibili
    assert routed_bilibili["zh"] == queries["video"]["zh"]
    assert "vi" not in routed_bilibili
    
    # Test with both platforms
    routed_both = route_video_queries(queries, ["youtube", "bilibili"])
    assert "vi" in routed_both
    assert "zh" in routed_both
    assert routed_both["vi"] == queries["video"]["vi"]
    assert routed_both["zh"] == queries["video"]["zh"]
    
    # Test with no matching platforms
    routed_none = route_video_queries(queries, ["facebook"])
    assert routed_none == {}

def test_start_job_request_model():
    """Test the StartJobRequest Pydantic model."""
    # Test with minimal data (only required field)
    request_data_minimal = {
        "query": "test query"
    }
    
    request_minimal = StartJobRequest(**request_data_minimal)
    assert request_minimal.query == "test query"
    assert request_minimal.top_amz == config.DEFAULT_TOP_AMZ
    assert request_minimal.top_ebay == config.DEFAULT_TOP_EBAY
    assert request_minimal.platforms == config.DEFAULT_PLATFORMS
    assert request_minimal.recency_days == config.DEFAULT_RECENCY_DAYS
    
    # Test with all fields provided
    request_data_full = {
        "query": "test query",
        "top_amz": 15,
        "top_ebay": 10,
        "platforms": ["youtube"],
        "recency_days": 15
    }
    
    request_full = StartJobRequest(**request_data_full)
    assert request_full.query == "test query"
    assert request_full.top_amz == 15
    assert request_full.top_ebay == 10
    assert request_full.platforms == ["youtube"]
    assert request_full.recency_days == 15

@pytest.mark.asyncio
async def test_call_ollama_success():
    """Test the call_ollama function with a successful response."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {"response": "test response"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = await call_ollama(
            model="test-model",
            prompt="test prompt",
            timeout_s=30
        )
        
        # Verify the result
        assert result == {"response": "test response"}
        
        # Verify the HTTP call
        mock_post.assert_called_once_with(
            f"{config.OLLAMA_HOST}/api/generate",
            json={
                "model": "test-model",
                "prompt": "test prompt",
                "stream": False,
                "options": {"timeout": 30000}
            },
            timeout=30
        )

@pytest.mark.asyncio
async def test_call_ollama_http_error():
    """Test the call_ollama function with an HTTP error."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=Mock(), response=Mock()
        )
        mock_post.return_value = mock_response
        
        with pytest.raises(HTTPException) as exc_info:
            await call_ollama(
                model="test-model",
                prompt="test prompt",
                timeout_s=30
            )

@pytest.mark.asyncio
async def test_call_ollama_request_error():
    """Test the call_ollama function with a request error."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.RequestError("Network error")
        
        with pytest.raises(HTTPException) as exc_info:
            await call_ollama(
                model="test-model",
                prompt="test prompt",
                timeout_s=30
            )

if __name__ == "__main__":
    # Run all tests
    test_build_cls_prompt()
    print("PASS: test_build_cls_prompt passed")

    test_build_gen_prompt()
    print("PASS: test_build_gen_prompt passed")

    test_normalize_queries()
    print("PASS: test_normalize_queries passed")

    test_route_video_queries()
    print("PASS: test_route_video_queries passed")

    test_start_job_request_model()
    print("PASS: test_start_job_request_model passed")

    print("\nAll unit tests passed!")