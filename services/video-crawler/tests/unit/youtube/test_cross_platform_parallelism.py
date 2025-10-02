from pathlib import Path
import asyncio
import os
import sys
import tempfile
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from fetcher.video_fetcher import VideoFetcher
from platform_crawler.interface import PlatformCrawlerInterface
from services.service import VideoCrawlerService

pytestmark = pytest.mark.unit

def build_service(mock_db, mock_broker, working_dir):
    """Create a service with mocked crawlers and temp keyframe paths."""
    with patch.object(VideoCrawlerService, "_initialize_platform_crawlers", return_value={}):
        service = VideoCrawlerService(mock_db, mock_broker, working_dir)
    service.initialize_keyframe_extractor(keyframe_dir=working_dir)
    return service

class MockPlatformCrawler(PlatformCrawlerInterface):
    """Mock platform crawler for testing parallelism"""

    def __init__(self, platform_name, delay_seconds=1):
        self.platform_name = platform_name
        self.delay_seconds = delay_seconds
        self.call_count = 0
        self.call_times = []  # Track when each call started

    async def search_and_download_videos(self, queries, recency_days, download_dir, num_videos):
        self.call_count += 1
        start_time = time.time()
        self.call_times.append(start_time)

        # Simulate processing delay
        await asyncio.sleep(self.delay_seconds)

        # Return mock videos
        return [
            {
                'platform': self.platform_name,
                'url': f'http://{self.platform_name}.com/video1',
                'title': f'{self.platform_name.title()} Video 1',
                'duration_s': 60,
                'video_id': f'{self.platform_name}_1',
                'local_path': f'{download_dir}/video1.mp4'
            }
        ]

    def get_platform_name(self):
        return self.platform_name


@pytest.mark.asyncio
async def test_cross_platform_parallelism():
    """Test that platforms run in parallel rather than sequentially (Acceptance Criteria #1)"""
    # Create mock database and broker
    mock_db = AsyncMock()
    mock_broker = AsyncMock()

    # Create service with mock crawlers
    with tempfile.TemporaryDirectory() as temp_dir:
        service = build_service(mock_db, mock_broker, temp_dir)

        # Replace platform crawlers with mock crawlers that have delays
        youtube_crawler = MockPlatformCrawler("youtube", delay_seconds=2)
        bilibili_crawler = MockPlatformCrawler("bilibili", delay_seconds=2)

        service.platform_crawlers = {
            "youtube": youtube_crawler,
            "bilibili": bilibili_crawler
        }
        service.video_fetcher = VideoFetcher(platform_crawlers=service.platform_crawlers)

        # Test event data with multiple platforms
        event_data = {
            "job_id": "test_job_123",
            "industry": "fashion",
            "queries": ["dress", "skirt"],
            "platforms": ["youtube", "bilibili"],
            "recency_days": 30
        }

        # Measure time to process multiple platforms
        start_time = time.time()
        await service.handle_videos_search_request(event_data)
        end_time = time.time()

        total_time = end_time - start_time

        # Verify both platforms were called
        assert youtube_crawler.call_count == 1
        assert bilibili_crawler.call_count == 1

        # Check that calls started at roughly the same time (parallel execution)
        assert len(youtube_crawler.call_times) == 1
        assert len(bilibili_crawler.call_times) == 1

        # If platforms ran sequentially, it would take ~4 seconds (2+2)
        # If platforms ran in parallel, it should take ~2 seconds
        assert total_time < 3, f"Platforms appear to run sequentially. Total time: {total_time:.2f}s"

        # Verify overlapping time windows (parallel execution)
        youtube_start = youtube_crawler.call_times[0]
        bilibili_start = bilibili_crawler.call_times[0]
        # They should start within a short time of each other (less than 0.5 seconds)
        assert abs(youtube_start - bilibili_start) < 0.5, "Platforms did not start in parallel"


@pytest.mark.asyncio
async def test_max_concurrent_platforms_limit():
    """Test that MAX_CONCURRENT_PLATFORMS limits concurrent platform execution (Acceptance Criteria #2)"""
    # Create mock database and broker
    mock_db = AsyncMock()
    mock_broker = AsyncMock()

    # Create service with mock crawlers
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock TikTokDownloader to use temporary directories
        with patch('platform_crawler.tiktok.tiktok_downloader.TikTokDownloader') as MockTikTokDownloader:
            mock_downloader_instance = MagicMock()
            mock_downloader_instance.video_storage_path = os.path.join(temp_dir, "tiktok_videos")
            mock_downloader_instance.keyframe_storage_path = os.path.join(temp_dir, "tiktok_keyframes")
            os.makedirs(mock_downloader_instance.video_storage_path, exist_ok=True)
            os.makedirs(mock_downloader_instance.keyframe_storage_path, exist_ok=True)
            MockTikTokDownloader.return_value = mock_downloader_instance

            # Mock TikTokCrawler to use the mocked downloader
            with patch('platform_crawler.tiktok.tiktok_crawler.TikTokCrawler') as MockTikTokCrawler:
                mock_tiktok_crawler_instance = MagicMock()
                mock_tiktok_crawler_instance.get_platform_name.return_value = "tiktok"
                mock_tiktok_crawler_instance.downloader = mock_downloader_instance
                MockTikTokCrawler.return_value = mock_tiktok_crawler_instance

                service = build_service(mock_db, mock_broker, temp_dir)

                # Replace platform crawlers with mock crawlers that have longer delays
                youtube_crawler = MockPlatformCrawler("youtube", delay_seconds=3)
                bilibili_crawler = MockPlatformCrawler("bilibili", delay_seconds=3)
                mock_crawler3 = MockPlatformCrawler("platform3", delay_seconds=3)

                service.platform_crawlers = {
                    "youtube": youtube_crawler,
                    "bilibili": bilibili_crawler,
                    "platform3": mock_crawler3,
                    "tiktok": mock_tiktok_crawler_instance  # Add mocked TikTok crawler
                }
                service.video_fetcher = VideoFetcher(platform_crawlers=service.platform_crawlers)

                # Test event data with multiple platforms
                event_data = {
                    "job_id": "test_job_456",
                    "industry": "tech",
                    "queries": ["smartphone", "laptop"],
                    "platforms": ["youtube", "bilibili", "platform3", "tiktok"],  # Add tiktok to platforms
                    "recency_days": 30
                }

                # Mock the config to limit concurrent platforms to 2
                with patch('services.service.config') as mock_config:
                    mock_config.NUM_VIDEOS = 5
                    mock_config.VIDEO_DIR = temp_dir
                    mock_config.MAX_CONCURRENT_PLATFORMS = 2  # Limit to 2 concurrent platforms

                    # Measure time to process platforms with concurrency limit
                    start_time = time.time()
                    await service.handle_videos_search_request(event_data)
                    end_time = time.time()

            total_time = end_time - start_time

            # Verify all platforms were called
            assert youtube_crawler.call_count == 1
            assert bilibili_crawler.call_count == 1
            assert mock_crawler3.call_count == 1

            # With 3 platforms and limit of 2 concurrent, should take ~6 seconds (3+3)
            # rather than 9 seconds (3+3+3) or 3 seconds (all concurrent)
            assert 5 <= total_time <= 7, f"Concurrency limit not working properly. Total time: {total_time:.2f}s"


@pytest.mark.asyncio
async def test_resilience_with_platform_failures():
    """Test resilience when one platform fails (Acceptance Criteria #3)"""
    # Create mock database and broker
    mock_db = AsyncMock()
    mock_broker = AsyncMock()

    # Create service with mock crawlers
    with tempfile.TemporaryDirectory() as temp_dir:
        service = build_service(mock_db, mock_broker, temp_dir)

        # Create a working crawler and a failing crawler
        working_crawler = MockPlatformCrawler("working", delay_seconds=1)

        class FailingPlatformCrawler(PlatformCrawlerInterface):
            async def search_and_download_videos(self, queries, recency_days, download_dir, num_videos):
                raise Exception("Simulated platform failure")

            def get_platform_name(self):
                return "failing"

        failing_crawler = FailingPlatformCrawler()

        service.platform_crawlers = {
            "working": working_crawler,
            "failing": failing_crawler
        }
        service.video_fetcher = VideoFetcher(platform_crawlers=service.platform_crawlers)

        # Test event data with both working and failing platforms
        event_data = {
            "job_id": "test_job_789",
            "industry": "fashion",
            "queries": ["dress"],
            "platforms": ["working", "failing"],
            "recency_days": 30
        }

        # This should not raise an exception even though one platform fails
        await service.handle_videos_search_request(event_data)

        # Verify that the working platform was called
        assert working_crawler.call_count == 1
        # The failing platform's exception should be caught and logged


@pytest.mark.asyncio
async def test_zero_result_path():
    """Test zero-result path (Acceptance Criteria #4)"""
    # Create mock database and broker
    mock_db = AsyncMock()
    mock_broker = AsyncMock()

    # Create service with mock crawlers that return empty results
    with tempfile.TemporaryDirectory() as temp_dir:
        service = build_service(mock_db, mock_broker, temp_dir)

        class EmptyPlatformCrawler(PlatformCrawlerInterface):
            async def search_and_download_videos(self, queries, recency_days, download_dir, num_videos):
                return []  # Return empty list

            def get_platform_name(self):
                return "empty"

        empty_crawler = EmptyPlatformCrawler()

        service.platform_crawlers = {
            "empty": empty_crawler
        }
        service.video_fetcher = VideoFetcher(platform_crawlers=service.platform_crawlers)

        # Test event data with platforms that return no videos
        event_data = {
            "job_id": "test_job_000",
            "industry": "fashion",
            "queries": ["nonexistent"],
            "platforms": ["empty"],
            "recency_days": 30
        }

        # This should not crash and should return empty results
        await service.handle_videos_search_request(event_data)

        # Verify that the event emitter was called to indicate completion
        assert service.event_emitter.broker.publish_event.called
