"""Unit tests for TikTokSearcher HTTP client."""
import pytest
pytestmark = pytest.mark.unit
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from platform_crawler.tiktok.tiktok_searcher import TikTokSearcher
from platform_crawler.tiktok.tiktok_models import TikTokSearchResponse


class TestTikTokSearcher:
    """Unit tests for TikTokSearcher."""
    
    @pytest.fixture
    def tiktok_searcher(self):
        """Create a TikTokSearcher instance for testing."""
        return TikTokSearcher("tiktok")
    
    @pytest.mark.asyncio
    async def test_search_tiktok_success(self, tiktok_searcher):
        """Test successful TikTok search."""
        # Mock response data
        mock_response_data = {
            "results": [
                {
                    "id": "123456789",
                    "caption": "Test video caption",
                    "authorHandle": "@testuser",
                    "likeCount": 1500,
                    "uploadTime": "2024-01-01T12:00:00Z",
                    "webViewUrl": "https://www.tiktok.com/@testuser/video/123456789"
                }
            ],
            "totalResults": 1,
            "query": "test query",
            "search_metadata": {
                "executed_path": "/tiktok/search",
                "execution_time": 200,
                "request_hash": "test-hash"
            }
        }
        
        # Create a mock response object
        mock_response = httpx.Response(
            status_code=200,
            json=mock_response_data
        )
        
        # Patch the client.post method
        with patch.object(tiktok_searcher.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            # Perform the search
            result = await tiktok_searcher.search_tiktok("test query", 5)
            
            # Assertions
            assert isinstance(result, TikTokSearchResponse)
            assert result.query == "test query"
            assert len(result.results) == 1
            assert result.results[0].id == "123456789"
            assert result.results[0].caption == "Test video caption"
            
            # Verify the API was called with correct parameters
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "http://localhost:5680/tiktok/search"
            assert call_args[1]["json"]["query"] == "test query"
            assert call_args[1]["json"]["numVideos"] == 5
            assert call_args[1]["json"]["force_headful"] is False
    
    @pytest.mark.asyncio
    async def test_search_tiktok_rate_limit_retry(self, tiktok_searcher):
        """Test TikTok search with rate limit that eventually succeeds."""
        # Mock successful response data
        mock_response_data = {
            "results": [],
            "totalResults": 0,
            "query": "retry test",
            "search_metadata": {}
        }
        
        # Create responses: first 429, then success
        rate_limit_response = httpx.Response(status_code=429, json={"error": "rate limited"})
        success_response = httpx.Response(status_code=200, json=mock_response_data)
        
        with patch.object(tiktok_searcher.client, 'post', side_effect=[
            rate_limit_response,  # First call returns 429
            success_response      # Second call returns success
        ]) as mock_post:
            # Mock asyncio.sleep to avoid actual delays during testing
            with patch('platform_crawler.tiktok.tiktok_searcher.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                result = await tiktok_searcher.search_tiktok("retry test", 5)
                
                # Should have been called twice (once for initial, once for retry)
                assert mock_post.call_count == 2
                # Should have slept once during the retry
                assert mock_sleep.call_count == 1
                # Verify successful result
                assert isinstance(result, TikTokSearchResponse)
                assert result.query == "retry test"
    
    @pytest.mark.asyncio
    async def test_search_tiktok_max_retries_exceeded(self, tiktok_searcher):
        """Test TikTok search that fails after max retries."""
        # Create a 429 response for rate limiting
        rate_limit_response = httpx.Response(status_code=429, json={"error": "rate limited"})
        
        with patch.object(tiktok_searcher.client, 'post', return_value=rate_limit_response) as mock_post:
            with patch('platform_crawler.tiktok.tiktok_searcher.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                # Should raise an exception after max retries (3)
                with pytest.raises(Exception, match="TikTok API rate limited after 3 attempts"):
                    await tiktok_searcher.search_tiktok("fail test", 5)
                
                # Should have been called 3 times (max attempts)
                assert mock_post.call_count == 3
                # Should have slept 2 times (between attempts)
                assert mock_sleep.call_count == 2
    
    @pytest.mark.asyncio
    async def test_search_tiktok_non_retryable_error(self, tiktok_searcher):
        """Test TikTok search with non-retryable error (400)."""
        # Create a 400 response for bad request (not retryable)
        bad_request_response = httpx.Response(status_code=400, json={"error": "bad request"})
        
        with patch.object(tiktok_searcher.client, 'post', return_value=bad_request_response) as mock_post:
            with patch('platform_crawler.tiktok.tiktok_searcher.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                # Should raise an exception immediately without retrying
                with pytest.raises(Exception, match="TikTok API bad request"):
                    await tiktok_searcher.search_tiktok("bad request test", 5)
                
                # Should have been called only once
                assert mock_post.call_count == 1
                # Should not have slept since it doesn't retry
                assert mock_sleep.call_count == 0
    
    @pytest.mark.asyncio
    async def test_search_tiktok_timeout_retry(self, tiktok_searcher):
        """Test TikTok search with timeout that eventually succeeds."""
        # Mock successful response data
        mock_response_data = {
            "results": [{"id": "test", "caption": "test", "authorHandle": "@test", 
                        "likeCount": 0, "uploadTime": "2024-01-01", "webViewUrl": "url"}],
            "totalResults": 1,
            "query": "timeout test",
            "search_metadata": {}
        }
        
        # Create timeout exception for first call, success for second
        with patch.object(tiktok_searcher.client, 'post', side_effect=[
            httpx.TimeoutException("Timeout"),  # First call times out
            httpx.Response(status_code=200, json=mock_response_data)  # Second call succeeds
        ]) as mock_post:
            with patch('platform_crawler.tiktok.tiktok_searcher.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                result = await tiktok_searcher.search_tiktok("timeout test", 5)
                
                # Should have been called twice (once for timeout, once for success)
                assert mock_post.call_count == 2
                # Should have slept once during the retry
                assert mock_sleep.call_count == 1
                # Verify successful result
                assert isinstance(result, TikTokSearchResponse)
                assert result.query == "timeout test"
    
    @pytest.mark.asyncio
    async def test_search_tiktok_json_decode_error(self, tiktok_searcher):
        """Test TikTok search with JSON decode error."""
        # Create a response with invalid JSON
        mock_response = httpx.Response(
            status_code=200,
            text="Invalid JSON response"
        )
        
        with patch.object(tiktok_searcher.client, 'post', return_value=mock_response) as mock_post:
            with pytest.raises(Exception, match="Invalid JSON response from TikTok API"):
                await tiktok_searcher.search_tiktok("json test", 5)
                
                # Should have been called once, then failed
                assert mock_post.call_count == 1