"""
Test suite for the main API service.
"""
import asyncio
import json
import sys
import os
import pytest
from unittest.mock import patch, AsyncMock, Mock
import httpx

# Add the libs directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs"))

# Add the current directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from config_loader import load_env, MainAPIConfig
from main import (
    build_cls_prompt, 
    build_gen_prompt, 
    normalize_queries, 
    route_video_queries,
    call_ollama,
    StartJobRequest
)


def test_build_cls_prompt():
    """Test the build_cls_prompt function."""
    query = "ergonomic office chair"
    industry_labels = ["fashion", "electronics", "office_products"]
    
    prompt = build_cls_prompt(query, industry_labels)
    
    # Check that the prompt contains the query
    assert query in prompt
    
    # Check that the prompt contains the industry labels
    for label in industry_labels:
        assert label in prompt
    
    # Check that the prompt has the required structure
    assert "Bạn là bộ phân loại zero-shot" in prompt
    assert "Chỉ in ra đúng 1 nhãn duy nhất" in prompt


def test_build_gen_prompt():
    """Test the build_gen_prompt function."""
    query = "ergonomic office chair"
    industry = "office_products"
    
    prompt = build_gen_prompt(query, industry)
    
    # Check that the prompt contains the query and industry
    assert query in prompt
    assert industry in prompt
    
    # Check that the prompt has the required structure
    assert "Bạn là bộ sinh từ khoá tìm kiếm đa ngôn ngữ" in prompt
    assert "product.en" in prompt
    assert "video.vi" in prompt
    assert "video.zh" in prompt


def test_normalize_queries():
    """Test the normalize_queries function."""
    # Test normal case
    queries = {
        "product": {
            "en": ["query 1", "query 2", "query 3"]
        },
        "video": {
            "vi": ["truy vấn 1", "truy vấn 2"],
            "zh": ["查询 1", "查询 2", "查询 3", "查询 4", "查询 5"]
        }
    }
    
    normalized = normalize_queries(queries, min_items=2, max_items=4)
    
    # Check product queries
    assert len(normalized["product"]["en"]) == 3  # Should not exceed max_items
    assert all(isinstance(q, str) for q in normalized["product"]["en"])
    
    # Check video queries
    assert len(normalized["video"]["vi"]) == 2  # Should stay within min/max
    assert len(normalized["video"]["zh"]) == 4  # Should be capped at max_items
    assert all(isinstance(q, str) for q in normalized["video"]["vi"])
    assert all(isinstance(q, str) for q in normalized["video"]["zh"])
    
    # Test case with insufficient items
    queries_insufficient = {
        "product": {
            "en": ["query 1"]
        },
        "video": {
            "vi": [],
            "zh": ["查询 1"]
        }
    }
    
    normalized_insufficient = normalize_queries(queries_insufficient, min_items=2, max_items=4)
    
    # Check the output (we expect padding when we have less than min_items but at least 1)
    assert len(normalized_insufficient["product"]["en"]) == 2  # Should be padded to min_items
    assert normalized_insufficient["product"]["en"][0] == "query 1"
    assert normalized_insufficient["product"]["en"][1] == "query 1"  # Padded with first item
    
    # Check that empty lists remain empty (no padding for empty lists)
    assert len(normalized_insufficient["video"]["vi"]) == 0  # Should remain empty
    
    # Check that insufficient items with 1 item are padded
    assert len(normalized_insufficient["video"]["zh"]) == 2  # Should be padded to min_items
    assert normalized_insufficient["video"]["zh"][0] == "查询 1"
    assert normalized_insufficient["video"]["zh"][1] == "查询 1"  # Padded with first item
    
    # Test empty input
    empty_queries = {}
    normalized_empty = normalize_queries(empty_queries, min_items=2, max_items=4)
    
    # Should return default structure with empty lists
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
    # Load config for default values
    try:
        config = load_env()
    except FileNotFoundError:
        config = MainAPIConfig(
            ollama_host="http://localhost:11434",
            model_classify="qwen3:4b-instruct",
            model_generate="qwen3:4b-instruct",
            ollama_timeout=60,
            industry_labels=["fashion","beauty_personal_care","books","electronics","home_garden","sports_outdoors","baby_products","pet_supplies","toys_games","automotive","office_products","business_industrial","collectibles_art","jewelry_watches","other"],
            default_top_amz=20,
            default_top_ebay=20,
            default_platforms=["youtube","bilibili"],
            default_recency_days=30
        )
    
    # Test with minimal data (only required field)
    request_data_minimal = {
        "query": "test query"
    }
    
    request_minimal = StartJobRequest(**request_data_minimal)
    assert request_minimal.query == "test query"
    assert request_minimal.top_amz == config.default_top_amz
    assert request_minimal.top_ebay == config.default_top_ebay
    assert request_minimal.platforms == config.default_platforms
    assert request_minimal.recency_days == config.default_recency_days
    
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
    
    # Test validation (missing required field)
    try:
        invalid_request = StartJobRequest(**{})
        assert False, "Should have raised validation error"
    except Exception:
        pass  # Expected


@pytest.mark.asyncio
async def test_call_ollama_success():
    """Test the call_ollama function with a successful response."""
    with patch("main.httpx.AsyncClient") as mock_client:
        # Mock the async context manager
        mock_async_client = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_async_client
        
        # Mock the response
        mock_response = Mock()
        mock_response.json.return_value = {"response": "test response"}
        mock_response.raise_for_status.return_value = None
        mock_async_client.post.return_value = mock_response
        
        # Call the function
        result = await call_ollama(
            model="test-model",
            prompt="test prompt",
            timeout_s=30
        )
        
        # Verify the result
        assert result == {"response": "test response"}
        
        # Verify the HTTP call was made correctly
        mock_async_client.post.assert_called_once_with(
            "http://host.docker.internal:11434/api/generate",
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
    with patch("main.httpx.AsyncClient") as mock_client:
        # Mock the async context manager
        mock_async_client = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_async_client
        
        # Mock the response to raise an HTTPStatusError
        from httpx import HTTPStatusError
        mock_async_client.post = AsyncMock(side_effect=HTTPStatusError(
            "Error", 
            request=Mock(), 
            response=Mock(status_code=500, text="Internal Server Error")
        ))
        
        # Call the function and expect an HTTPException
        from fastapi import HTTPException
        try:
            await call_ollama(
                model="test-model",
                prompt="test prompt",
                timeout_s=30
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert "Ollama request failed" in str(e.detail)
            assert "Internal Server Error" in str(e.detail)


@pytest.mark.asyncio
async def test_call_ollama_request_error():
    """Test the call_ollama function with a request error."""
    with patch("main.httpx.AsyncClient") as mock_client:
        # Mock the async context manager
        mock_async_client = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_async_client
        
        # Mock the response to raise a RequestError
        from httpx import RequestError
        mock_async_client.post = AsyncMock(side_effect=RequestError("Connection error"))
        
        # Call the function and expect an HTTPException
        from fastapi import HTTPException
        try:
            await call_ollama(
                model="test-model",
                prompt="test prompt",
                timeout_s=30
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert "Ollama request failed" in str(e.detail)
            assert "Connection error" in str(e.detail)


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
    print("Note: Async tests require pytest to run properly")