import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest

from fetcher.video_fetcher import VideoFetcher
from platform_crawler.interface import PlatformCrawlerInterface
from platform_crawler.mock_crawler import MockPlatformCrawler
from services.service import VideoCrawlerService


pytestmark = pytest.mark.integration

# Mock VideoFrameCRUD since it's external dependency
VideoFrameCRUD = MagicMock


class TestVideoCrawlerIntegration:
    """Test the integration between VideoCrawlerService, VideoFetcher, and PlatformCrawler"""
    
    @pytest.fixture
    def temp_data_root(self):
        """Create a temporary directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def mock_db(self):
        """Mock database manager"""
        return MagicMock()
    
    @pytest.fixture
    def mock_broker(self):
        """Mock message broker"""
        broker = MagicMock()
        broker.publish_event = AsyncMock()
        return broker
    
    @pytest.fixture
    def video_crawler_service(self, mock_db, mock_broker, temp_data_root):
        """Create VideoCrawlerService with mocked dependencies"""
        service = VideoCrawlerService(mock_db, mock_broker, temp_data_root)
        # Mock the VideoFrameCRUD
        service.frame_crud = MagicMock(spec=VideoFrameCRUD)
        service.frame_crud.create_video_frame = AsyncMock(return_value="mock_frame_id")
        return service
    
    @pytest.fixture
    def video_fetcher_with_crawlers(self, temp_data_root):
        """Create VideoFetcher with platform crawlers"""
        crawlers = {
            "youtube": MockPlatformCrawler("youtube"),
            "bilibili": MockPlatformCrawler("bilibili"),
            "douyin": MockPlatformCrawler("douyin")
        }
        return VideoFetcher(platform_crawlers=crawlers)
    
    @pytest.mark.asyncio
    async def test_video_fetcher_with_platform_crawlers(self, video_fetcher_with_crawlers, temp_data_root):
        """Test that VideoFetcher can use platform crawlers with new cross-platform method"""
        queries = ["test query"]
        recency_days = 7
        download_dirs = {
            "youtube": os.path.join(temp_data_root, "videos", "youtube"),
            "bilibili": os.path.join(temp_data_root, "videos", "bilibili")
        }
        
        # Test cross-platform search
        all_videos = await video_fetcher_with_crawlers.search_all_platforms_videos_parallel(
            platforms=["youtube", "bilibili"],
            queries=queries,
            recency_days=recency_days,
            download_dirs=download_dirs,
            num_videos=5,
            job_id="test-job-123"
        )
        
        assert len(all_videos) > 0, "Cross-platform search should return videos"
        # Check that we have videos from both platforms
        youtube_videos = [v for v in all_videos if v["platform"] == "youtube"]
        bilibili_videos = [v for v in all_videos if v["platform"] == "bilibili"]
        assert len(youtube_videos) > 0, "Should have YouTube videos"
        assert len(bilibili_videos) > 0, "Should have Bilibili videos"
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, video_crawler_service):
        """Test that VideoCrawlerService initializes with platform crawlers"""
        assert video_crawler_service.platform_crawlers is not None
        assert "youtube" in video_crawler_service.platform_crawlers
        assert "bilibili" in video_crawler_service.platform_crawlers
        assert "douyin" in video_crawler_service.platform_crawlers
        assert "tiktok" in video_crawler_service.platform_crawlers

        # Verify that VideoFetcher has access to platform crawlers
        assert video_crawler_service.video_fetcher.platform_crawlers is not None
        assert len(video_crawler_service.video_fetcher.platform_crawlers) == 4
    
    
    @pytest.mark.asyncio
    async def test_handle_videos_search_request_integration(self, video_crawler_service):
        """Test the complete video search request flow"""
        event_data = {
            "job_id": "test-job-123",
            "industry": "fashion",
            "queries": ["summer dresses", "casual wear"],
            "platforms": ["youtube", "bilibili"],
            "recency_days": 30
        }
        
        # Mock database operations
        video_crawler_service.db.execute = AsyncMock()
        
        # Call the method
        await video_crawler_service.handle_videos_search_request(event_data)
        
        # Verify that the event emitter was called (indicating the flow completed)
        assert video_crawler_service.event_emitter.broker.publish_event.called
        
        # Check that batch keyframes ready event was published
        batch_calls = [
            event_call
            for event_call in video_crawler_service.event_emitter.broker.publish_event.call_args_list
            if event_call[0][0] == "videos.keyframes.ready.batch"
        ]
        assert len(batch_calls) > 0, "Batch keyframes ready event should be published"
        
        # Check that videos collections completed event was published
        collection_calls = [
            event_call
            for event_call in video_crawler_service.event_emitter.broker.publish_event.call_args_list
            if event_call[0][0] == "videos.collections.completed"
        ]
        assert len(collection_calls) > 0, "Videos collections completed event should be published"
    
    @pytest.mark.asyncio
    async def test_unsupported_platform_handling(self, video_crawler_service):
        """Test handling of unsupported platforms with new method"""
        queries = ["test query"]
        recency_days = 7
        download_dirs = {
            "unsupported_platform": "/tmp/test"
        }
        
        videos = await video_crawler_service.video_fetcher.search_all_platforms_videos_parallel(
            platforms=["unsupported_platform"],
            queries=queries,
            recency_days=recency_days,
            download_dirs=download_dirs,
            num_videos=5,
            job_id="test-job-456"
        )
        
        assert len(videos) == 0, "Unsupported platform should return no videos"
    
    def test_platform_crawler_interface(self):
        """Test that MockPlatformCrawler implements the interface correctly"""
        crawler = MockPlatformCrawler("test_platform")
        
        # Verify it implements the interface
        assert isinstance(crawler, PlatformCrawlerInterface)
        
        # Verify it has the required method
        assert hasattr(crawler, 'search_and_download_videos')
        assert asyncio.iscoroutinefunction(crawler.search_and_download_videos)