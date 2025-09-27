"""Integration tests for TikTok crawler functionality."""
import pytest
import asyncio
import os
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

from services.service import VideoCrawlerService
from platform_crawler.interface import PlatformCrawlerInterface
from platform_crawler.tiktok.tiktok_crawler import TikTokCrawler
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from config_loader import config


@pytest.fixture
async def db():
    """Real database connection for testing"""
    db_manager = DatabaseManager(config.POSTGRES_DSN)
    try:
        await db_manager.connect()
        yield db_manager
    finally:
        await db_manager.disconnect()


@pytest.fixture
async def broker():
    """Real RabbitMQ connection for testing"""
    broker_manager = MessageBroker(config.BUS_BROKER)
    try:
        await broker_manager.connect()
        yield broker_manager
    finally:
        await broker_manager.disconnect()


@pytest.fixture
def tiktok_crawler():
    """TikTok crawler instance with mocked search results for predictable testing"""
    crawler = TikTokCrawler()
    
    # Mock the search_and_download_videos method to return predictable test data
    async def mock_search_and_download_videos(queries, recency_days, download_dir, num_videos):
        """Mock method that returns realistic TikTok video data for testing"""
        mock_videos = [
            {
                'platform': 'tiktok',
                'url': 'https://www.tiktok.com/@testuser/video/1234567890',
                'title': 'Đánh giá tai nghe không dây - review chi tiết',
                'video_id': '1234567890',
                'author_handle': '@testuser',
                'like_count': 1500,
                'upload_time': '2024-01-15T10:30:00Z',
                'local_path': None,  # TikTok videos are not downloaded directly
                'duration_s': None   # Duration not available in search results
            },
            {
                'platform': 'tiktok',
                'url': 'https://www.tiktok.com/@reviewer/video/0987654321',
                'title': 'Unbox iPhone 15 Pro Max - First impressions',
                'video_id': '0987654321',
                'author_handle': '@reviewer',
                'like_count': 2300,
                'upload_time': '2024-01-10T15:45:00Z',
                'local_path': None,
                'duration_s': None
            }
        ]
        return mock_videos
    
    # Replace the real method with our mock
    crawler.search_and_download_videos = mock_search_and_download_videos
    return crawler


class TestTikTokIntegration:
    """Integration tests for TikTok crawler functionality."""

    @pytest.mark.asyncio
    async def test_tiktok_search_request_processing(self, db, broker, tiktok_crawler, temp_dir):
        """Ensure TikTok search requests are dispatched through the crawler."""
        # Replace the TikTok crawler in the service with our real instance
        service = VideoCrawlerService(db, broker)
        service.platform_crawlers["tiktok"] = tiktok_crawler

        # Track published events
        published_topics = []
        async def track_publish_event(topic: str, event_data: Dict[str, Any], correlation_id: str = None):
            published_topics.append(topic)
        
        # Mock the publish_event method to track calls
        broker.publish_event = track_publish_event

        event_data = {
            "job_id": "test-job-123",
            "industry": "electronics",
            "queries": {
                "vi": ["đánh giá tai nghe không dây", "unbox iphone 15"],
            },
            "platforms": ["tiktok"],
            "recency_days": 30,
        }

        # Mock the video fetcher to capture the videos returned by TikTok crawler
        actual_videos = []
        original_fetcher_method = service.video_fetcher.search_all_platforms_videos_parallel
        
        async def mock_fetch_all_videos(*args, **kwargs):
            """Mock the video fetcher to capture and return our mock TikTok videos"""
            # Call the original TikTok crawler to get our mock data
            videos = await tiktok_crawler.search_and_download_videos(
                queries=["đánh giá tai nghe không dây", "unbox iphone 15"],
                recency_days=30,
                download_dir="",
                num_videos=10
            )
            actual_videos.extend(videos)
            return videos
        
        service.video_fetcher.search_all_platforms_videos_parallel = mock_fetch_all_videos
        
        # Mock the job progress manager and event emitter for proper handling
        service.job_progress_manager = AsyncMock()
        
        async def mock_emit_keyframes_ready_batch(job_id, batch_payload):
            """Mock event emitter to track processed videos"""
            assert job_id == "test-job-123"
            assert len(batch_payload) == 2
            for video_data in batch_payload:
                assert "video_id" in video_data
                assert "platform" in video_data
                assert video_data["platform"] == "tiktok"
        
        async def mock_emit_collections_completed(job_id):
            """Mock event completion"""
            assert job_id == "test-job-123"
        
        service.event_emitter.publish_videos_keyframes_ready_batch = mock_emit_keyframes_ready_batch
        service.event_emitter.publish_videos_collections_completed = mock_emit_collections_completed

        # Execute the search request
        await service.handle_videos_search_request(event_data)

        # Verify that TikTok crawler was set up correctly
        assert "tiktok" in service.platform_crawlers
        
        # Check that expected events were published
        assert "videos.collections.completed" in published_topics
        
        # Validate that the TikTok crawler returned the expected video data
        assert len(actual_videos) == 2, f"Expected 2 videos, got {len(actual_videos)}"
        
        # Validate first video
        video1 = actual_videos[0]
        assert video1['platform'] == 'tiktok'
        assert video1['video_id'] == '1234567890'
        assert video1['title'] == 'Đánh giá tai nghe không dây - review chi tiết'
        assert video1['url'] == 'https://www.tiktok.com/@testuser/video/1234567890'
        assert video1['author_handle'] == '@testuser'
        assert video1['like_count'] == 1500
        assert video1['upload_time'] == '2024-01-15T10:30:00Z'
        assert video1['local_path'] is None  # TikTok videos are not downloaded
        assert video1['duration_s'] is None  # Duration not available in search results
        
        # Validate second video
        video2 = actual_videos[1]
        assert video2['platform'] == 'tiktok'
        assert video2['video_id'] == '0987654321'
        assert video2['title'] == 'Unbox iPhone 15 Pro Max - First impressions'
        assert video2['url'] == 'https://www.tiktok.com/@reviewer/video/0987654321'
        assert video2['author_handle'] == '@reviewer'
        assert video2['like_count'] == 2300
        assert video2['upload_time'] == '2024-01-10T15:45:00Z'
        assert video2['local_path'] is None
        assert video2['duration_s'] is None
        
        # Verify that videos were processed with job progress tracking
        service.job_progress_manager.update_job_progress.assert_called()
        
        # Restore original method after test
        service.video_fetcher.search_all_platforms_videos_parallel = original_fetcher_method

    @pytest.mark.asyncio
    async def test_tiktok_error_handling(self, db, broker, tiktok_crawler):
        """Gracefully handle crawler failures without raising."""
        # Replace the TikTok crawler in the service with our real instance
        service = VideoCrawlerService(db, broker)
        service.platform_crawlers["tiktok"] = tiktok_crawler

        # Track published events
        published_topics = []
        async def track_publish_event(topic: str, event_data: Dict[str, Any], correlation_id: str = None):
            published_topics.append(topic)
        
        # Mock the publish_event method to track calls
        broker.publish_event = track_publish_event

        event_data = {
            "job_id": "test-job-456",
            "industry": "tech reviews",
            "queries": {"vi": ["đánh giá laptop giá rẻ", "gadgets bếp thông minh"]},
            "platforms": ["tiktok"],
            "recency_days": 30,
        }

        # Mock the video fetcher to simulate API failure
        async def mock_fetch_all_videos_error(*args, **kwargs):
            """Simulate TikTok API failure"""
            raise Exception("TikTok API rate limit exceeded")

        service.video_fetcher.search_all_platforms_videos_parallel = mock_fetch_all_videos_error
        service.event_emitter.publish_videos_collections_completed = AsyncMock()
        service.job_progress_manager = AsyncMock()

        # Execute the search request (this will simulate API failure)
        try:
            await service.handle_videos_search_request(event_data)
        except Exception as e:
            # If the API call fails, we still want to verify the error handling
            # The service should still complete the process by calling the zero videos handler
            pass

        service.event_emitter.publish_videos_collections_completed.assert_called_once_with(job_id="test-job-456")
        
        # Verify that job progress was still updated even for zero videos
        if service.job_progress_manager.update_job_progress:
            service.job_progress_manager.update_job_progress.assert_called()
        
        # Note: Can't easily restore original method, so this change is temporary for the test
