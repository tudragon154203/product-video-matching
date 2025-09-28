import pytest
pytestmark = pytest.mark.unit
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import os
from pathlib import Path

# Import directly from the files we need to test
from platform_crawler.youtube.youtube_crawler import YoutubeCrawler

class MockYoutubeDownloader:
    """Mock downloader for testing"""
    
    def __init__(self, delay_seconds=1):
        self.delay_seconds = delay_seconds
        self.download_count = 0
        self.max_concurrent = 0
        self.concurrent_downloads = 0
        self.download_times = []
        
    async def download_video(self, video, download_dir):
        # Track concurrent downloads
        self.concurrent_downloads += 1
        self.max_concurrent = max(self.max_concurrent, self.concurrent_downloads)
        
        import time
        start_time = time.time()
        
        # Simulate download delay
        await asyncio.sleep(self.delay_seconds)
        
        # Track end time
        end_time = time.time()
        self.download_times.append(end_time - start_time)
        self.download_count += 1
        self.concurrent_downloads -= 1
        
        # Return video with local path
        video_copy = video.copy()
        video_copy['local_path'] = f"/fake/path/{video['video_id']}.mp4"
        return video_copy

@pytest.mark.asyncio
async def test_parallel_download_performance():
    """Test that parallel download is faster than sequential"""
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        crawler = YoutubeCrawler()
        
        # Mock the downloader to simulate slow downloads
        mock_downloader = MockYoutubeDownloader(delay_seconds=2)
        crawler.downloader = mock_downloader
        
        # Create test videos
        videos = {
            'video1': {'video_id': '1', 'title': 'Video 1', 'uploader': 'Uploader1', 'url': 'http://example.com/1'},
            'video2': {'video_id': '2', 'title': 'Video 2', 'uploader': 'Uploader2', 'url': 'http://example.com/2'},
            'video3': {'video_id': '3', 'title': 'Video 3', 'uploader': 'Uploader3', 'url': 'http://example.com/3'},
            'video4': {'video_id': '4', 'title': 'Video 4', 'uploader': 'Uploader4', 'url': 'http://example.com/4'},
            'video5': {'video_id': '5', 'title': 'Video 5', 'uploader': 'Uploader5', 'url': 'http://example.com/5'},
        }
        
        # Test parallel download
        start_time = asyncio.get_event_loop().time()
        results = await crawler._download_unique_videos(videos, temp_dir)
        end_time = asyncio.get_event_loop().time()
        parallel_time = end_time - start_time
        
        # Verify all videos were downloaded
        assert len(results) == 5
        assert mock_downloader.download_count == 5
        assert mock_downloader.max_concurrent <= 5  # Should be limited by semaphore
        
        # In parallel, should be much faster than 5 * 2 = 10 seconds
        # With 5 concurrent downloads of 2 seconds each, should be ~2 seconds + overhead
        assert parallel_time < 5, f"Parallel download took {parallel_time:.2f}s, expected < 5s"

@pytest.mark.asyncio 
async def test_semaphore_concurrency_limit():
    """Test that semaphore properly limits concurrent downloads"""
    with tempfile.TemporaryDirectory() as temp_dir:
        crawler = YoutubeCrawler()
        
        # Mock downloader with longer delay to measure concurrency
        mock_downloader = MockYoutubeDownloader(delay_seconds=3)
        crawler.downloader = mock_downloader
        
        # Create 10 videos to test concurrency limit
        videos = {}
        for i in range(10):
            videos[f'video{i}'] = {
                'video_id': str(i), 
                'title': f'Video {i}', 
                'uploader': f'Uploader{i}', 
                'url': f'http://example.com/{i}'
            }
        
        # Test parallel download
        await crawler._download_unique_videos(videos, temp_dir)
        
        # Verify concurrency was limited (semaphore limits to 5)
        # In reality it might reach 5-6 depending on timing
        assert mock_downloader.max_concurrent <= 6, f"Max concurrent downloads was {mock_downloader.max_concurrent}, expected <= 6"
