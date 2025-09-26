"""Integration tests for TikTok crawler functionality."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.service import VideoCrawlerService
from platform_crawler.interface import PlatformCrawlerInterface


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_broker():
    broker = MagicMock()
    broker.publish_event = AsyncMock()
    return broker


class TestTikTokIntegration:
    """Integration tests for TikTok crawler functionality."""

    @pytest.mark.asyncio
    async def test_tiktok_platform_integration(self, mock_db, mock_broker):
        """Verify TikTok platform is wired into the service."""
        service = VideoCrawlerService(mock_db, mock_broker)

        assert "tiktok" in service.platform_crawlers
        assert isinstance(service.platform_crawlers["tiktok"], PlatformCrawlerInterface)
        assert "tiktok" in service.video_fetcher.platform_crawlers

    @pytest.mark.asyncio
    async def test_tiktok_search_request_processing(self, mock_db, mock_broker):
        """Ensure TikTok search requests are dispatched through the crawler."""
        service = VideoCrawlerService(mock_db, mock_broker)

        mock_tiktok_crawler = AsyncMock()
        mock_tiktok_crawler.search_and_download_videos.return_value = [
            {
                "platform": "tiktok",
                "url": "https://www.tiktok.com/@testuser/video/123456789",
                "title": "Test TikTok Video",
                "video_id": "123456789",
                "local_path": "/tmp/video.mp4",
            }
        ]
        service.platform_crawlers["tiktok"] = mock_tiktok_crawler

        service.process_video = AsyncMock(return_value={
            "video_id": "generated-video-id",
            "platform": "tiktok",
            "frames": [],
        })

        event_data = {
            "job_id": "test-job-123",
            "industry": "test industry",
            "queries": {
                "vi": ["test query vietnamese"],
                "zh": ["test query chinese"],
            },
            "platforms": ["tiktok"],
            "recency_days": 30,
        }

        await service.handle_videos_search_request(event_data)

        mock_tiktok_crawler.search_and_download_videos.assert_awaited_once()
        service.process_video.assert_awaited()

        published_topics = [call.args[0] for call in mock_broker.publish_event.call_args_list]
        assert "videos.collections.completed" in published_topics
        assert "videos.keyframes.ready.batch" in published_topics

    @pytest.mark.asyncio
    async def test_tiktok_platform_query_extraction(self, mock_db, mock_broker):
        """TikTok queries should prioritize Vietnamese inputs."""
        service = VideoCrawlerService(mock_db, mock_broker)

        queries = {
            "vi": ["query vi 1", "query vi 2"],
            "zh": ["query zh 1", "query zh 2"],
        }

        extracted_queries = service._extract_platform_queries(queries, ["tiktok"])

        assert extracted_queries == ["query vi 1", "query vi 2"]

    @pytest.mark.asyncio
    async def test_tiktok_error_handling(self, mock_db, mock_broker):
        """Gracefully handle crawler failures without raising."""
        service = VideoCrawlerService(mock_db, mock_broker)

        mock_tiktok_crawler = AsyncMock()
        mock_tiktok_crawler.search_and_download_videos.side_effect = Exception("TikTok API unavailable")
        service.platform_crawlers["tiktok"] = mock_tiktok_crawler

        event_data = {
            "job_id": "test-job-456",
            "industry": "test industry",
            "queries": {"vi": ["test query"]},
            "platforms": ["tiktok"],
            "recency_days": 30,
        }

        await service.handle_videos_search_request(event_data)

        mock_tiktok_crawler.search_and_download_videos.assert_awaited_once()
        published_topics = [call.args[0] for call in mock_broker.publish_event.call_args_list]
        assert "videos.collections.completed" in published_topics
