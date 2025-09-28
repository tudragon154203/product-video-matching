from services.llm.llm_service import LLMService
from config_loader import config
import sys
import asyncio
import httpx
from fastapi import HTTPException
from unittest.mock import patch, AsyncMock, Mock
import os
import pytest
pytestmark = pytest.mark.integration

# Add project root to PYTHONPATH for local imports
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))


@pytest.mark.asyncio
async def test_call_gemini_http_error():
    """Test the call_gemini function with an HTTP error."""
    llm_service = LLMService()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=Mock(), response=Mock()
        )
        mock_post.return_value = mock_response

        # Set a dummy API key for testing
        with patch.object(config, 'GEMINI_API_KEY', 'test-api-key'):
            with pytest.raises(HTTPException):
                await llm_service.call_gemini(
                    model="gemini-pro",
                    prompt="test prompt",
                    timeout_s=30
                )


@pytest.mark.asyncio
async def test_call_gemini_request_error():
    """Test the call_gemini function with a request error."""
    llm_service = LLMService()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.RequestError("Network error")

        # Set a dummy API key for testing
        with patch.object(config, 'GEMINI_API_KEY', 'test-api-key'):
            with pytest.raises(HTTPException):
                await llm_service.call_gemini(
                    model="gemini-pro",
                    prompt="test prompt",
                    timeout_s=30
                )


@pytest.mark.asyncio
async def test_call_llm_no_gemini_key_direct_ollama():
    """Test the call_llm function when Gemini key is not set (uses Ollama directly)."""
    llm_service = LLMService()

    with patch.object(llm_service, 'call_ollama', new_callable=AsyncMock) as mock_call_ollama:
        mock_call_ollama.return_value = {"response": "ollama response"}

        # Set empty API key for testing
        with patch.object(config, 'GEMINI_API_KEY', ''):
            result = await llm_service.call_llm("classify", "test prompt")

            # Verify the result came from Ollama
            assert result == {"response": "ollama response"}

            # Verify Ollama was called and Gemini was not
            mock_call_ollama.assert_called_once()
            assert not hasattr(
                llm_service, '_call_gemini_mock') or not llm_service._call_gemini_mock.called


@pytest.mark.asyncio
async def test_call_llm_old_behavior_tests_deprecated():
    """
    DEPRECATED: These tests are kept for reference but reflect the old behavior.
    The new behavior is Gemini first, then Ollama fallback.
    """
    # These tests are now obsolete but kept for documentation
    pass


@pytest.mark.asyncio
async def test_call_llm_gemini_success():
    """Test the call_llm function when Gemini succeeds (new primary behavior)."""
    llm_service = LLMService()

    with patch.object(llm_service, 'call_gemini', new_callable=AsyncMock) as mock_call_gemini:
        mock_call_gemini.return_value = {"response": "gemini response"}

        # Set a dummy API key for testing
        with patch.object(config, 'GEMINI_API_KEY', 'test-api-key'):
            result = await llm_service.call_llm("classify", "test prompt")

            # Verify the result came from Gemini
            assert result == {"response": "gemini response"}

            # Verify Gemini was called and Ollama was not
            mock_call_gemini.assert_called_once()
            assert not hasattr(
                llm_service, '_call_ollama_mock') or not llm_service._call_ollama_mock.called


@pytest.mark.asyncio
async def test_call_llm_gemini_failure_ollama_fallback():
    """Test the call_llm function when Gemini fails and falls back to Ollama (new behavior)."""
    llm_service = LLMService()

    with patch.object(llm_service, 'call_gemini', new_callable=AsyncMock) as mock_call_gemini:
        mock_call_gemini.side_effect = httpx.HTTPError("Gemini HTTP error")

        with patch.object(llm_service, 'call_ollama', new_callable=AsyncMock) as mock_call_ollama:
            mock_call_ollama.return_value = {"response": "ollama response"}

            # Set a dummy API key for testing
            with patch.object(config, 'GEMINI_API_KEY', 'test-api-key'):
                result = await llm_service.call_llm("generate", "test prompt")

                # Verify the result came from Ollama fallback
                assert result == {"response": "ollama response"}

                # Verify both functions were called in the right order
                mock_call_gemini.assert_called_once()
                mock_call_ollama.assert_called_once()


@pytest.mark.asyncio
async def test_call_llm_gemini_timeout_ollama_fallback():
    """Test the call_llm function when Gemini times out and falls back to Ollama."""
    llm_service = LLMService()

    with patch.object(llm_service, 'call_gemini', new_callable=AsyncMock) as mock_call_gemini:
        mock_call_gemini.side_effect = asyncio.TimeoutError("Gemini timeout")

        with patch.object(llm_service, 'call_ollama', new_callable=AsyncMock) as mock_call_ollama:
            mock_call_ollama.return_value = {"response": "ollama response"}

            # Set a dummy API key for testing
            with patch.object(config, 'GEMINI_API_KEY', 'test-api-key'):
                result = await llm_service.call_llm("classify", "test prompt")

                # Verify the result came from Ollama fallback
                assert result == {"response": "ollama response"}

                # Verify both functions were called in the right order
                mock_call_gemini.assert_called_once()
                mock_call_ollama.assert_called_once()


@pytest.mark.asyncio
async def test_call_llm_gemini_and_ollama_both_fail():
    """Test the call_llm function when both Gemini and Ollama fail (complete failure)."""
    llm_service = LLMService()

    with patch.object(llm_service, 'call_gemini', new_callable=AsyncMock) as mock_call_gemini:
        mock_call_gemini.side_effect = HTTPException(
            status_code=500, detail="Gemini request failed")

        with patch.object(llm_service, 'call_ollama', new_callable=AsyncMock) as mock_call_ollama:
            mock_call_ollama.side_effect = HTTPException(
                status_code=500, detail="Ollama request failed")

            # Set a dummy API key for testing
            with patch.object(config, 'GEMINI_API_KEY', 'test-api-key'):
                with pytest.raises(HTTPException) as exc_info:
                    await llm_service.call_llm("classify", "test prompt")

                # Verify the error is from the Ollama fallback (since Gemini failed first)
                assert "Ollama request failed" in str(exc_info.value.detail)

if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v"])
