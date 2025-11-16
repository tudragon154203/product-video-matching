"""Unit tests for TikTokSearcher HTTP client."""

import httpx
from unittest.mock import AsyncMock, patch

import pytest

from platform_crawler.tiktok.tiktok_models import TikTokSearchResponse
from platform_crawler.tiktok.tiktok_searcher import TikTokSearcher
from config_loader import config

pytestmark = pytest.mark.unit


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
            assert call_args[0][0] == f"http://{config.TIKTOK_CRAWL_HOST}:{config.TIKTOK_CRAWL_HOST_PORT}/tiktok/search"
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
                # Should raise an exception after max retries (2)
                with pytest.raises(Exception, match="TikTok API rate limited after 2 attempts"):
                    await tiktok_searcher.search_tiktok("fail test", 5)

                # Should have been called 2 times (max attempts)
                assert mock_post.call_count == 2
                # Should have slept 1 time (between attempts)
                assert mock_sleep.call_count == 1

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

    @pytest.mark.asyncio
    async def test_force_headful_on_second_attempt(self, tiktok_searcher):
        """Test that force_headful is set to true on the second attempt."""
        # Mock response data
        mock_response_data = {
            "results": [
                {
                    "id": "123",
                    "caption": "Test",
                    "authorHandle": "@test",
                    "likeCount": 100,
                    "uploadTime": "2024-01-01T12:00:00Z",
                    "webViewUrl": "https://www.tiktok.com/@test/video/123"
                }
            ],
            "totalResults": 1,
            "query": "test",
            "search_metadata": {}
        }

        # First attempt fails, second succeeds
        error_response = httpx.Response(status_code=500, json={"error": "server error"})
        success_response = httpx.Response(status_code=200, json=mock_response_data)

        with patch.object(tiktok_searcher.client, 'post', side_effect=[
            error_response,
            success_response
        ]) as mock_post:
            with patch('platform_crawler.tiktok.tiktok_searcher.asyncio.sleep', new_callable=AsyncMock):
                result = await tiktok_searcher.search_tiktok("test", 5)

                # Verify both calls were made
                assert mock_post.call_count == 2

                # First call should have force_headful=False
                first_call_json = mock_post.call_args_list[0][1]["json"]
                assert first_call_json["force_headful"] is False

                # Second call should have force_headful=True
                second_call_json = mock_post.call_args_list[1][1]["json"]
                assert second_call_json["force_headful"] is True

                # Result should be successful
                assert isinstance(result, TikTokSearchResponse)

    @pytest.mark.asyncio
    async def test_force_headful_remembered_after_success(self, tiktok_searcher):
        """Test that force_headful is remembered and used for subsequent searches."""
        # Mock response data
        mock_response_data = {
            "results": [
                {
                    "id": "123",
                    "caption": "Test",
                    "authorHandle": "@test",
                    "likeCount": 100,
                    "uploadTime": "2024-01-01T12:00:00Z",
                    "webViewUrl": "https://www.tiktok.com/@test/video/123"
                }
            ],
            "totalResults": 1,
            "query": "test",
            "search_metadata": {}
        }

        # First search: fail on first attempt, succeed on second with force_headful
        error_response = httpx.Response(status_code=500, json={"error": "server error"})
        success_response = httpx.Response(status_code=200, json=mock_response_data)

        with patch.object(tiktok_searcher.client, 'post', side_effect=[
            error_response,      # First search, first attempt fails
            success_response,    # First search, second attempt succeeds with force_headful
            success_response,    # Second search, first attempt with force_headful
        ]) as mock_post:
            with patch('platform_crawler.tiktok.tiktok_searcher.asyncio.sleep', new_callable=AsyncMock):
                # First search - should try twice
                result1 = await tiktok_searcher.search_tiktok("test1", 5)
                assert isinstance(result1, TikTokSearchResponse)
                assert mock_post.call_count == 2

                # Verify force_headful flag is now set
                assert tiktok_searcher._use_force_headful is True

                # Second search - should use force_headful immediately
                result2 = await tiktok_searcher.search_tiktok("test2", 5)
                assert isinstance(result2, TikTokSearchResponse)
                assert mock_post.call_count == 3

                # Verify the third call (second search) used force_headful=True immediately
                third_call_json = mock_post.call_args_list[2][1]["json"]
                assert third_call_json["force_headful"] is True
                assert third_call_json["query"] == "test2"

    @pytest.mark.asyncio
    async def test_force_headful_not_set_on_first_attempt_success(self, tiktok_searcher):
        """Test that force_headful flag is not set if first attempt succeeds."""
        # Mock response data
        mock_response_data = {
            "results": [
                {
                    "id": "123",
                    "caption": "Test",
                    "authorHandle": "@test",
                    "likeCount": 100,
                    "uploadTime": "2024-01-01T12:00:00Z",
                    "webViewUrl": "https://www.tiktok.com/@test/video/123"
                }
            ],
            "totalResults": 1,
            "query": "test",
            "search_metadata": {}
        }

        success_response = httpx.Response(status_code=200, json=mock_response_data)

        with patch.object(tiktok_searcher.client, 'post', return_value=success_response) as mock_post:
            # First search succeeds on first attempt
            result = await tiktok_searcher.search_tiktok("test", 5)
            assert isinstance(result, TikTokSearchResponse)
            assert mock_post.call_count == 1

            # Verify force_headful flag is NOT set
            assert tiktok_searcher._use_force_headful is False

            # First call should have force_headful=False
            first_call_json = mock_post.call_args_list[0][1]["json"]
            assert first_call_json["force_headful"] is False

    @pytest.mark.asyncio
    async def test_force_headful_used_immediately_when_already_set(self, tiktok_searcher):
        """Test that force_headful is used immediately if already learned."""
        # Manually set the flag as if it was learned from a previous search
        tiktok_searcher._use_force_headful = True

        # Mock response data
        mock_response_data = {
            "results": [
                {
                    "id": "123",
                    "caption": "Test",
                    "authorHandle": "@test",
                    "likeCount": 100,
                    "uploadTime": "2024-01-01T12:00:00Z",
                    "webViewUrl": "https://www.tiktok.com/@test/video/123"
                }
            ],
            "totalResults": 1,
            "query": "test",
            "search_metadata": {}
        }

        success_response = httpx.Response(status_code=200, json=mock_response_data)

        with patch.object(tiktok_searcher.client, 'post', return_value=success_response) as mock_post:
            # Search should succeed on first attempt with force_headful=True
            result = await tiktok_searcher.search_tiktok("test", 5)
            assert isinstance(result, TikTokSearchResponse)
            assert mock_post.call_count == 1

            # Verify the call used force_headful=True
            call_json = mock_post.call_args_list[0][1]["json"]
            assert call_json["force_headful"] is True
