"""
Unit tests for the Gemini service without requiring API access.
"""
from services.llm.prompt_service import PromptService
from services.llm.llm_service import LLMService
from config_loader import config
import httpx
from fastapi import HTTPException
from unittest.mock import patch, AsyncMock, Mock
import pytest
import sys
import os

# Add the libs directory to the path
sys.path.append(os.path.join(os.path.dirname(
    __file__), "..", "..", "..", "libs"))

# Add the current directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

pytestmark = pytest.mark.unit


def test_build_cls_prompt():
    """Test building classification prompt."""
    prompt_service = PromptService()
    query = "ergonomic office chair"
    labels = ["office_products", "electronics", "fashion"]

    prompt = prompt_service.build_cls_prompt(query, labels)

    assert query in prompt
    for label in labels:
        assert label in prompt


def test_build_gen_prompt():
    """Test building generation prompt."""
    prompt_service = PromptService()
    query = "ergonomic office chair"
    industry = "office_products"

    prompt = prompt_service.build_gen_prompt(query, industry)

    assert query in prompt
    assert industry in prompt
    assert "JSON" in prompt


def test_normalize_queries():
    """Test query normalization."""
    prompt_service = PromptService()

    # Test normal case
    queries = {
        "product": {"en": ["query1", "query2", "query3"]},
        "video": {
            "vi": ["video1", "video2"],
            "zh": ["视频1", "视频2"]
        }
    }

    normalized = prompt_service.normalize_queries(queries)

    assert "product" in normalized
    assert "video" in normalized
    assert len(normalized["product"]["en"]) == 3
    assert len(normalized["video"]["vi"]) == 2
    assert len(normalized["video"]["zh"]) == 2


@patch("httpx.AsyncClient.post")
@pytest.mark.asyncio
async def test_call_gemini_success(mock_post):
    """Test successful Gemini API call."""
    # Create mock response
    mock_response = Mock()
    mock_response.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{"text": "test response"}]
            }
        }]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    # Create LLM service
    llm_service = LLMService()

    # Test with a dummy API key
    with patch.object(config, 'GEMINI_API_KEY', 'test-key'):
        result = await llm_service.call_gemini(
            model="gemini-pro",
            prompt="test prompt",
            timeout_s=30
        )

        assert result["response"] == "test response"
        mock_post.assert_called_once()


@patch("httpx.AsyncClient.post")
@pytest.mark.asyncio
async def test_call_gemini_http_error(mock_post):
    """Test Gemini API call with HTTP error."""
    mock_post.side_effect = httpx.HTTPStatusError(
        "Error", request=Mock(), response=Mock()
    )

    llm_service = LLMService()

    with patch.object(config, 'GEMINI_API_KEY', 'test-key'):
        with pytest.raises(HTTPException):
            await llm_service.call_gemini(
                model="gemini-pro",
                prompt="test prompt",
                timeout_s=30
            )


@patch("httpx.AsyncClient.post")
@pytest.mark.asyncio
async def test_call_gemini_request_error(mock_post):
    """Test Gemini API call with request error."""
    mock_post.side_effect = httpx.RequestError("Network error")

    llm_service = LLMService()

    with patch.object(config, 'GEMINI_API_KEY', 'test-key'):
        with pytest.raises(HTTPException):
            await llm_service.call_gemini(
                model="gemini-pro",
                prompt="test prompt",
                timeout_s=30
            )


@pytest.mark.asyncio
async def test_call_llm_gemini_success():
    """Test call_llm function with Gemini fallback."""
    llm_service = LLMService()

    # Mock Ollama to fail and Gemini to succeed
    with patch.object(llm_service, 'call_ollama', side_effect=Exception("Ollama error")):
        with patch.object(llm_service, 'call_gemini', new_callable=AsyncMock) as mock_call_gemini:
            mock_call_gemini.return_value = {"response": "gemini response"}

            with patch.object(config, 'GEMINI_API_KEY', 'test-key'):
                result = await llm_service.call_llm("classify", "test prompt")

                # Verify the result came from Gemini
                assert result == {"response": "gemini response"}
                mock_call_gemini.assert_called_once()

if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v"])
