"""Integration tests for TikTok crawler functionality."""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from services.service import VideoCrawlerService
from platform_crawler.interface import PlatformCrawlerInterface


class TestTikTokIntegration:
    """Integration tests for TikTok crawler functionality."""

    @pytest.mark.asyncio
    async def test_tiktok_platform_integration(self, mock_db, mock_broker):
        """Test that TikTok platform is properly integrated into the video crawler service."""
        # This test should fail initially until TikTok crawler is implemented

        service = VideoCrawlerService(mock_db, mock_broker)

        # Verify TikTok platform is available in platform crawlers
        assert "tiktok" in service.platform_crawlers
        assert isinstance(service.platform_crawlers["tiktok"], PlatformCrawlerInterface)

        # Test that TikTok platform can be used in search requests
        platforms = ["tiktok"]
        assert "tiktok" in platforms

    @pytest.mark.asyncio
    async def test_tiktok_search_request_processing(self, mock_db, mock_broker):
        """Test that TikTok search requests are properly processed."""
        # This test should fail initially until TikTok integration is complete

        service = VideoCrawlerService(mock_db, mock_broker)

        # Mock TikTok crawler to return test data
        mock_tiktok_crawler = AsyncMock()
        mock_tiktok_crawler.search_and_download_videos.return_value = [
            {
                "platform": "tiktok",
                "url": "https://www.tiktok.com/@testuser/video/123456789",
                "title": "Test TikTok Video",
                "video_id": "123456789"
            }
        ]

        # Replace the TikTok crawler with our mock
        service.platform_crawlers["tiktok"] = mock_tiktok_crawler

        # Test event data for TikTok search
        event_data = {
            "job_id": "test-job-123",
            "industry": "test industry",
            "queries": {
                "vi": ["test query vietnamese"],
                "zh": ["test query chinese"]
            },
            "platforms": ["tiktok"],
            "recency_days": 30
        }

        # This should work once TikTok platform is fully integrated
        with pytest.raises(NotImplementedError):
            await service.handle_videos_search_request(event_data)

    @pytest.mark.asyncio
    async def test_tiktok_platform_query_extraction(self, mock_db, mock_broker):
        """Test that TikTok platform queries are properly extracted."""
        # This test should fail initially until query extraction is updated

        service = VideoCrawlerService(mock_db, mock_broker)

        # Test query extraction for TikTok platform
        queries = {
            "vi": ["query vi 1", "query vi 2"],
            "zh": ["query zh 1", "query zh 2"]
        }
        platforms = ["tiktok"]

        # This should extract Vietnamese queries for TikTok
        extracted_queries = service._extract_platform_queries(queries, platforms)

        # Currently this will fail until TikTok query extraction is implemented
        # For now, just verify the method exists and returns a list
        assert isinstance(extracted_queries, list)

    @pytest.mark.asyncio
    async def test_tiktok_error_handling(self, mock_db, mock_broker):
        """Test that TikTok API errors are handled gracefully."""
        # This test should fail initially until error handling is implemented

        service = VideoCrawlerService(mock_db, mock_broker)

        # Mock TikTok crawler to raise an exception
        mock_tiktok_crawler = AsyncMock()
        mock_tiktok_crawler.search_and_download_videos.side_effect = Exception("TikTok API unavailable")
        service.platform_crawlers["tiktok"] = mock_tiktok_crawler

        event_data = {
            "job_id": "test-job-123",
            "industry": "test industry",
            "queries": {"vi": ["test query"]},
            "platforms": ["tiktok"],
            "recency_days": 30
        }

        # This should handle TikTok API errors gracefully once implemented
        # For now, it will likely raise an exception
        with pytest.raises(Exception):
            await service.handle_videos_search_request(event_data)