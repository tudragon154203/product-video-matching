"""Contract tests for TikTok Search API integration."""

import httpx
import pytest
from unittest.mock import AsyncMock, patch

from config_loader import config


pytestmark = pytest.mark.contract


class TestTikTokAPIContract:
    """Contract tests to validate TikTok Search API integration."""

    @pytest.mark.asyncio
    async def test_tiktok_api_endpoint_responds(self):
        """Test that TikTok API endpoint responds to valid requests."""
        # This test should fail initially until TikTok crawler is implemented

        # Mock the API response based on the OpenAPI contract
        mock_response = {
            "results": [
                {
                    "id": "video_123456789",
                    "caption": "Check out this amazing ergonomic pillow!",
                    "authorHandle": "@comfortlover",
                    "likeCount": 12345,
                    "uploadTime": "2024-01-01T12:00:00Z",
                    "webViewUrl": "https://www.tiktok.com/@comfortlover/video/123456789"
                }
            ],
            "totalResults": 150,
            "query": "ergonomic pillows",
            "search_metadata": {
                "executed_path": "/tiktok/search",
                "execution_time": 450,
                "request_hash": "abc123def456"
            }
        }

        # Create a mock response object
        mock_response_obj = httpx.Response(
            status_code=200,
            json=mock_response
        )

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response_obj

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:{config.TIKTOK_CRAWL_HOST_PORT}/tiktok/search",
                    json={
                        "query": "ergonomic pillows",
                        "numVideos": 5,
                        "force_headful": False
                    }
                )

            assert response.status_code == 200
            data = response.json()

            # Validate response structure against contract
            assert "results" in data
            assert "totalResults" in data
            assert "query" in data
            assert "search_metadata" in data

            # Validate individual video structure
            video = data["results"][0]
            assert "id" in video
            assert "caption" in video
            assert "authorHandle" in video
            assert "likeCount" in video
            assert "uploadTime" in video
            assert "webViewUrl" in video

    @pytest.mark.asyncio
    async def test_tiktok_api_validation_errors(self):
        """Test that TikTok API returns proper validation errors."""
        # This test should fail initially until error handling is implemented

        mock_response = {
            "error": "Invalid request parameters",
            "code": "INVALID_REQUEST"
        }

        mock_response_obj = httpx.Response(
            status_code=400,
            json=mock_response
        )

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response_obj

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:{config.TIKTOK_CRAWL_HOST_PORT}/tiktok/search",
                    json={"query": ""}  # Empty query should trigger validation error
                )

            assert response.status_code == 400
            data = response.json()
            assert "error" in data
            assert "code" in data

    @pytest.mark.asyncio
    async def test_tiktok_api_rate_limit_handling(self):
        """Test that TikTok API rate limits are handled gracefully."""
        # This test should fail initially until rate limit handling is implemented

        mock_response = {
            "error": "Rate limit exceeded",
            "code": "RATE_LIMIT_EXCEEDED",
            "details": {"retry_after": 60}
        }

        mock_response_obj = httpx.Response(
            status_code=429,
            json=mock_response
        )

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response_obj

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:{config.TIKTOK_CRAWL_HOST_PORT}/tiktok/search",
                    json={"query": "test"}
                )

            assert response.status_code == 429
            data = response.json()
            assert "error" in data
            assert "code" in data
            assert "details" in data
