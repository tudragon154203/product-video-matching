import os
import pytest
from unittest.mock import patch, AsyncMock, Mock
from fastapi import HTTPException
import httpx

# Add project root to PYTHONPATH for local imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config_loader import config
from services.prompt_service import PromptService
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker

# Create mock instances for testing
mock_db = Mock(spec=DatabaseManager)
mock_broker = Mock(spec=MessageBroker)
prompt_service = PromptService()

def test_build_cls_prompt():
    """Test the build_cls_prompt function."""
    test_query = "ergonomic office chair"
    prompt = prompt_service.build_cls_prompt(test_query, config.INDUSTRY_LABELS)
    assert "ergonomic office chair" in prompt
    assert "Classify this query into one industry label" in prompt
    assert "Labels" in prompt
    assert "Output only the label name" in prompt

def test_build_gen_prompt():
    """Test the build_gen_prompt function."""
    test_query = "ergonomic office chair"
    industry = "office_products"
    prompt = prompt_service.build_gen_prompt(test_query, industry)
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
            "vi": ["truy\u1ebfn 1", "truy\u1ebfn 2"],
            "zh": ["\u67e5\u8be2 1", "\u67e5\u8be2 2"]
        }
    }
    normalized = prompt_service.normalize_queries(queries)
    assert normalized == queries

    # Test with missing product queries
    queries_no_product = {
        "video": {
            "vi": ["truy\u1ebfn 1"]
        }
    }
    normalized_no_product = prompt_service.normalize_queries(queries_no_product)
    assert normalized_no_product == {
        "product": {"en": []},
        "video": {"vi": ["truy\u1ebfn 1", "truy\u1ebfn 1"], "zh": []}
    }

    # Test with empty queries
    queries_empty = {}
    normalized_empty = prompt_service.normalize_queries(queries_empty)
    assert normalized_empty == {
        "product": {"en": []},
        "video": {"vi": [], "zh": []}
    }

def test_route_video_queries():
    """Test the route_video_queries function."""
    queries = {
        "video": {
            "vi": ["truy\u1ebfn 1", "truy\u1ebfn 2"],
            "zh": ["\u67e5\u8be2 1", "\u67e5\u8be2 2"]
        }
    }
    
    # Test with YouTube platform (should get vi queries)
    routed_youtube = prompt_service.route_video_queries(queries, ["youtube"])
    assert "vi" in routed_youtube
    assert routed_youtube["vi"] == queries["video"]["vi"]
    # Both keys are always present due to initialization
    assert "zh" in routed_youtube
    assert routed_youtube["zh"] == []
    
    # Test with Bilibili platform (should get zh queries)
    routed_bilibili = prompt_service.route_video_queries(queries, ["bilibili"])
    assert "zh" in routed_bilibili
    assert routed_bilibili["zh"] == queries["video"]["zh"]
    assert "vi" in routed_bilibili
    assert routed_bilibili["vi"] == []
    
    # Test with both platforms
    routed_both = prompt_service.route_video_queries(queries, ["youtube", "bilibili"])
    assert "vi" in routed_both
    assert "zh" in routed_both
    assert routed_both["vi"] == queries["video"]["vi"]
    assert routed_both["zh"] == queries["video"]["zh"]
    
    # Test with no matching platforms
    routed_none = prompt_service.route_video_queries(queries, ["facebook"])
    assert routed_none == {"vi": [], "zh": []}

def test_start_job_request_model():
    """Test the StartJobRequest Pydantic model."""
    from models.schemas import StartJobRequest
    
    # Test with minimal data (only required field)
    request_data_minimal = {
        "query": "test query",
        "top_amz": 20,
        "top_ebay": 20,
        "platforms": ["youtube", "bilibili"],
        "recency_days": 30
    }
    
    request_minimal = StartJobRequest(**request_data_minimal)
    assert request_minimal.query == "test query"
    assert request_minimal.top_amz == 20
    assert request_minimal.top_ebay == 20
    assert request_minimal.platforms == ["youtube", "bilibili"]
    assert request_minimal.recency_days == 30
    
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
    # This test is now in test_llm_fallback.py since call_ollama is in LLMService
    
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