"""
Integration tests for the Gemini service that make real API calls.
"""
from services.llm.prompt_service import PromptService
from services.llm.llm_service import LLMService
from config_loader import config
import os
import sys
import httpx
from fastapi import HTTPException
from unittest.mock import patch, Mock
import pytest

# Add the libs directory to the path
sys.path.append(os.path.join(os.path.dirname(
    __file__), "..", "..", "..", "libs"))

# Add the current directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_call_gemini_real_api():
    """Test calling Gemini API with real API key from environment."""
    # Check if GEMINI_API_KEY is set
    if not config.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY not set, skipping real API test")

    llm_service = LLMService()

    result = await llm_service.call_gemini(
        model=config.GEMINI_MODEL,
        prompt="Say 'Hello, World!' in a single sentence.",
        timeout_s=30
    )

    assert "response" in result
    assert isinstance(result["response"], str)
    assert len(result["response"]) > 0


@pytest.mark.asyncio
async def test_full_llm_flow_with_real_gemini():
    """Test the full LLM flow using real Gemini API."""
    # Check if GEMINI_API_KEY is set
    if not config.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY not set, skipping real API test")

    llm_service = LLMService()
    prompt_service = PromptService()

    # Test with a simple prompt
    prompt = prompt_service.build_gen_prompt("simple test", "general")

    result = await llm_service.call_llm("generate", prompt)

    assert "response" in result
    assert isinstance(result["response"], str)


@pytest.mark.asyncio
async def test_call_gemini_success():
    """Test successful Gemini API call with mocked response."""
    # Check if GEMINI_API_KEY is set
    if not config.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY not set, skipping test")

    # Local imports removed - now available at module level

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

    llm_service = LLMService()

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await llm_service.call_gemini(
            model="gemini-2.5-flash",
            prompt="test prompt",
            timeout_s=30
        )

        assert result["response"] == "test response"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_call_gemini_http_error():
    """Test Gemini API call with HTTP error."""
    # Check if GEMINI_API_KEY is set
    if not config.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY not set, skipping test")

    # Local imports removed - now available at module level

    llm_service = LLMService()

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = httpx.HTTPStatusError(
            "Error", request=Mock(), response=Mock()
        )

        with pytest.raises(HTTPException):
            await llm_service.call_gemini(
                model="gemini-2.5-flash",
                prompt="test prompt",
                timeout_s=30
            )


@pytest.mark.asyncio
async def test_call_gemini_request_error():
    """Test Gemini API call with request error."""
    # Check if GEMINI_API_KEY is set
    if not config.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY not set, skipping test")

    # Local imports removed - now available at module level

    llm_service = LLMService()

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = httpx.RequestError("Network error")

        with pytest.raises(HTTPException):
            await llm_service.call_gemini(
                model="gemini-2.5-flash",
                prompt="test prompt",
                timeout_s=30
            )


@pytest.mark.asyncio
async def test_call_llm_gemini_success():
    """Test call_llm function with Gemini fallback."""
    # Check if GEMINI_API_KEY is set
    if not config.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY not set, skipping test")

    llm_service = LLMService()

    # Mock Ollama to fail and Gemini to succeed
    with patch.object(llm_service, 'call_ollama', side_effect=Exception("Ollama error")):
        with patch.object(llm_service, 'call_gemini', return_value={"response": "gemini response"}):

            result = await llm_service.call_llm("classify", "test prompt")

            # Verify the result came from Gemini
            assert result == {"response": "gemini response"}
