"""
Unit tests for TikTok Crawler
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from platform_crawler.tiktok.tiktok_crawler import TikTokCrawler


class TestTikTokCrawler:
    """Test cases for TikTokCrawler"""
    
    @pytest.fixture
    def crawler(self):
        """Create TikTokCrawler instance for testing"""
        return TikTokCrawler()
    
    def test_platform_name(self, crawler):
        """Test platform name is correct"""
        assert crawler.get_platform_name() == "tiktok"
    
    @pytest.mark.asyncio
    async def test_search_and_download_videos_success(
        self, crawler, temp_dir, mock_video_data, mock_downloaded_video_data
    ):
        """Test successful search and download"""
        with patch.object(crawler, '_search_videos') as mock_search, \
             patch.object(crawler, '_download_videos') as mock_download:
            
            mock_search.return_value = mock_video_data
            mock_download.return_value = mock_downloaded_video_data
            
            results = await crawler.search_and_download_videos(
                queries=["test query"],
                recency_days=7,
                download_dir=temp_dir,
                num_videos=5
            )
            
            assert len(results) == 2
            assert all(video["platform"] == "tiktok" for video in results)
            assert all("local_path" in video for video in results)
            
            # Verify methods were called
            mock_search.assert_called_once_with(["test query"], 7, 5)
            mock_download.assert_called_once_with(mock_video_data, temp_dir)
    
    @pytest.mark.asyncio
    async def test_search_and_download_empty_queries(self, crawler, temp_dir):
        """Test with empty query list"""
        results = await crawler.search_and_download_videos(
            queries=[],
            recency_days=7,
            download_dir=temp_dir,
            num_videos=5
        )
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_search_and_download_no_results(self, crawler, temp_dir):
        """Test when search returns no results"""
        with patch.object(crawler, '_search_videos') as mock_search:
            mock_search.return_value = []
            
            results = await crawler.search_and_download_videos(
                queries=["test query"],
                recency_days=7,
                download_dir=temp_dir,
                num_videos=5
            )
            
            assert results == []
    
    @pytest.mark.asyncio
    async def test_search_videos_vietnam_region(self, crawler):
        """Test search with Vietnam region optimization"""
        with patch('platform_crawler.tiktok.tiktok_crawler.config') as mock_config, \
             patch.object(crawler.searcher, 'search_vietnamese_content') as mock_vn_search:
            
            mock_config.TIKTOK_VIETNAM_REGION = True
            mock_vn_search.return_value = []
            
            await crawler._search_videos(["test"], 7, 5)
            
            mock_vn_search.assert_called_once_with(["test"], 7, 5)
    
    @pytest.mark.asyncio
    async def test_search_videos_general(self, crawler):
        """Test search with general keyword search"""
        with patch('platform_crawler.tiktok.tiktok_crawler.config') as mock_config, \
             patch.object(crawler.searcher, 'search_videos_by_keywords') as mock_search:
            
            mock_config.TIKTOK_VIETNAM_REGION = False
            mock_search.return_value = []
            
            await crawler._search_videos(["test"], 7, 5)
            
            mock_search.assert_called_once_with(["test"], 7, 5)
    
    @pytest.mark.asyncio
    async def test_download_videos_success(self, crawler, mock_video_data, temp_dir):
        """Test successful video download"""
        with patch('platform_crawler.tiktok.tiktok_crawler.TikTokDownloader') as mock_downloader_class:
            mock_downloader_instance = AsyncMock()
            mock_downloader_instance.download_multiple_videos.return_value = mock_video_data
            mock_downloader_class.return_value.__aenter__.return_value = mock_downloader_instance
            
            results = await crawler._download_videos(mock_video_data, temp_dir)
            
            assert results == mock_video_data
            mock_downloader_instance.download_multiple_videos.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_videos_empty_list(self, crawler, temp_dir):
        """Test download with empty video list"""
        results = await crawler._download_videos([], temp_dir)
        assert results == []
    
    def test_format_results_success(self, crawler, mock_downloaded_video_data):
        """Test successful result formatting"""
        formatted = crawler._format_results(mock_downloaded_video_data)
        
        assert len(formatted) == 2
        
        for video in formatted:
            assert video["platform"] == "tiktok"
            assert "url" in video
            assert "title" in video
            assert "video_id" in video
            assert "local_path" in video
            assert "duration_s" in video
    
    def test_format_results_skip_without_local_path(self, crawler, mock_video_data):
        """Test formatting skips videos without local_path"""
        # Remove local_path from videos
        incomplete_results = mock_video_data.copy()
        
        formatted = crawler._format_results(incomplete_results)
        
        # Should skip videos without local_path
        assert len(formatted) == 0
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, crawler):
        """Test successful health check"""
        with patch.object(crawler.searcher, 'search_videos_by_keywords') as mock_search:
            mock_search.return_value = [{"video_id": "test"}]
            
            is_healthy = await crawler.health_check()
            
            assert is_healthy is True
            mock_search.assert_called_once_with(queries=["test"], recency_days=7, num_videos=1)
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, crawler):
        """Test health check failure"""
        with patch.object(crawler.searcher, 'search_videos_by_keywords') as mock_search:
            mock_search.return_value = []
            
            is_healthy = await crawler.health_check()
            
            assert is_healthy is True  # Even 0 results means API is working
    
    @pytest.mark.asyncio
    async def test_health_check_exception(self, crawler):
        """Test health check with exception"""
        with patch.object(crawler.searcher, 'search_videos_by_keywords') as mock_search:
            mock_search.side_effect = Exception("API error")
            
            is_healthy = await crawler.health_check()
            
            assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_search_and_download_creates_directory(self, crawler):
        """Test that download directory is created if it doesn't exist"""
        with tempfile.TemporaryDirectory() as temp_base:
            non_existent_dir = Path(temp_base) / "new_dir"
            
            with patch.object(crawler, '_search_videos') as mock_search, \
                 patch.object(crawler, '_download_videos') as mock_download:
                
                mock_search.return_value = []
                mock_download.return_value = []
                
                await crawler.search_and_download_videos(
                    queries=["test"],
                    recency_days=7,
                    download_dir=str(non_existent_dir),
                    num_videos=5
                )
                
                assert non_existent_dir.exists()
                assert non_existent_dir.is_dir()
    
    @pytest.mark.asyncio
    async def test_search_and_download_with_exception(self, crawler, temp_dir):
        """Test search and download with exception handling"""
        with patch.object(crawler, '_search_videos') as mock_search:
            mock_search.side_effect = Exception("Search failed")
            
            results = await crawler.search_and_download_videos(
                queries=["test"],
                recency_days=7,
                download_dir=temp_dir,
                num_videos=5
            )
            
            assert results == []