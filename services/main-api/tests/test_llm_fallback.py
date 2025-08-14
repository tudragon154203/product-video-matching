import os
import pytest
from unittest.mock import patch, AsyncMock, Mock
from fastapi import HTTPException
import httpx
import asyncio

# Add project root to PYTHONPATH for local imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config_loader import config
from services.llm_service import LLMService

@pytest.mark.asyncio
async def test_call_gemini_success():
    """Test the call_gemini function with a successful response."""
    llm_service = LLMService()
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
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
        
        # Set a dummy API key for testing
        with patch.object(config, 'GEMINI_API_KEY', 'test-api-key'):
            result = await llm_service.call_gemini(
                model="gemini-pro",
                prompt="test prompt",
                timeout_s=30
            )
            
            # Verify the result
            assert result == {"response": "test response"}
            
            # Verify the HTTP call
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
            assert kwargs["headers"] == {"x-goog-api-key": "test-api-key"}
            # Timeout is set on the client, not the post method

@pytest.mark.asyncio
async def test_call_gemini_no_api_key():
    """Test the call_gemini function when no API key is set."""
    llm_service = LLMService()
    
    # Test with empty API key
    with patch.object(config, 'GEMINI_API_KEY', ''):
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not set"):
            await llm_service.call_gemini(
                model="gemini-pro",
                prompt="test prompt",
                timeout_s=30
            )

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
            with pytest.raises(HTTPException) as exc_info:
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
            with pytest.raises(HTTPException) as exc_info:
                await llm_service.call_gemini(
                    model="gemini-pro",
                    prompt="test prompt",
                    timeout_s=30
                )

@pytest.mark.asyncio
async def test_call_llm_ollama_success():
    """Test the call_llm function when Ollama succeeds."""
    llm_service = LLMService()
    
    with patch.object(llm_service, 'call_ollama', new_callable=AsyncMock) as mock_call_ollama:
        mock_call_ollama.return_value = {"response": "test response"}
        
        result = await llm_service.call_llm("classify", "test prompt")
        
        # Verify the result
        assert result == {"response": "test response"}
        
        # Verify Ollama was called
        mock_call_ollama.assert_called_once()

@pytest.mark.asyncio
async def test_call_llm_ollama_timeout_fallback_to_gemini():
    """Test the call_llm function when Ollama times out and falls back to Gemini."""
    llm_service = LLMService()
    
    with patch.object(llm_service, 'call_ollama', new_callable=AsyncMock) as mock_call_ollama:
        mock_call_ollama.side_effect = asyncio.TimeoutError("Ollama timeout")
        
        with patch.object(llm_service, 'call_gemini', new_callable=AsyncMock) as mock_call_gemini:
            mock_call_gemini.return_value = {"response": "gemini response"}
            
            # Set a dummy API key for testing
            with patch.object(config, 'GEMINI_API_KEY', 'test-api-key'):
                result = await llm_service.call_llm("classify", "test prompt")
                
                # Verify the result came from Gemini
                assert result == {"response": "gemini response"}
                
                # Verify both functions were called
                mock_call_ollama.assert_called_once()
                mock_call_gemini.assert_called_once()

@pytest.mark.asyncio
async def test_call_llm_ollama_http_error_fallback_to_gemini():
    """Test the call_llm function when Ollama returns HTTP error and falls back to Gemini."""
    llm_service = LLMService()
    
    with patch.object(llm_service, 'call_ollama', new_callable=AsyncMock) as mock_call_ollama:
        mock_call_ollama.side_effect = httpx.HTTPError("Ollama HTTP error")
        
        with patch.object(llm_service, 'call_gemini', new_callable=AsyncMock) as mock_call_gemini:
            mock_call_gemini.return_value = {"response": "gemini response"}
            
            # Set a dummy API key for testing
            with patch.object(config, 'GEMINI_API_KEY', 'test-api-key'):
                result = await llm_service.call_llm("generate", "test prompt")
                
                # Verify the result came from Gemini
                assert result == {"response": "gemini response"}
                
                # Verify both functions were called
                mock_call_ollama.assert_called_once()
                mock_call_gemini.assert_called_once()

@pytest.mark.asyncio
async def test_call_llm_ollama_timeout_no_gemini_key():
    """Test the call_llm function when Ollama times out and Gemini key is not set."""
    llm_service = LLMService()
    
    with patch.object(llm_service, 'call_ollama', new_callable=AsyncMock) as mock_call_ollama:
        mock_call_ollama.side_effect = asyncio.TimeoutError("Ollama timeout")
        
        # Set empty API key for testing
        with patch.object(config, 'GEMINI_API_KEY', ''):
            with pytest.raises(asyncio.TimeoutError, match="Ollama timeout"):
                await llm_service.call_llm("classify", "test prompt")
                
            # Verify Ollama was called
            mock_call_ollama.assert_called_once()

@pytest.mark.asyncio
async def test_call_llm_ollama_http_error_no_gemini_key():
    """Test the call_llm function when Ollama returns HTTP error and Gemini key is not set."""
    llm_service = LLMService()
    
    with patch.object(llm_service, 'call_ollama', new_callable=AsyncMock) as mock_call_ollama:
        mock_call_ollama.side_effect = httpx.HTTPError("Ollama HTTP error")
        
        # Set empty API key for testing
        with patch.object(config, 'GEMINI_API_KEY', ''):
            with pytest.raises(httpx.HTTPError, match="Ollama HTTP error"):
                await llm_service.call_llm("generate", "test prompt")
                
            # Verify Ollama was called
            mock_call_ollama.assert_called_once()

if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v"])