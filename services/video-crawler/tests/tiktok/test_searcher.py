"""
Unit tests for TikTok Searcher
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from platform_crawler.tiktok.tiktok_searcher import TikTokSearcher


class TestTikTokSearcher:
    """Test cases for TikTokSearcher"""
    
    @pytest.fixture
    def searcher(self):
        """Create TikTokSearcher instance for testing"""
        return TikTokSearcher("tiktok")
    
    @pytest.mark.asyncio
    async def test_search_videos_by_keywords_success(self, searcher, mock_video_data):
        """Test successful keyword search"""
        with patch('platform_crawler.tiktok.tiktok_searcher.TikTokApiClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.search_videos.return_value = mock_video_data
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            results = await searcher.search_videos_by_keywords(
                queries=["test query"],
                recency_days=7,
                num_videos=10
            )
            
            assert len(results) == 2
            assert results[0]["video_id"] == "test_video_1"
    
    def test_apply_filters_recency(self, searcher, mock_video_data):
        """Test recency filtering"""
        import time
        current_time = time.time()
        
        # Modify video times to test filtering
        test_data = mock_video_data.copy()
        test_data[0]["create_time"] = current_time - 3600  # 1 hour ago
        test_data[1]["create_time"] = current_time - (8 * 24 * 3600)  # 8 days ago
        
        filtered = searcher._apply_filters(test_data, recency_days=7, min_duration=0, max_duration=300)
        
        # Should exclude test_data[1] (8 days old)
        assert len(filtered) == 1
        assert filtered[0]["video_id"] == "test_video_1"
    
    def test_apply_filters_duration(self, searcher, mock_video_data):
        """Test duration filtering"""
        # Update mock data with current timestamps to pass recency filter
        import time
        current_time = time.time()
        test_data = mock_video_data.copy()
        test_data[0]["create_time"] = current_time - 3600  # 1 hour ago
        test_data[1]["create_time"] = current_time - 7200  # 2 hours ago
        
        filtered = searcher._apply_filters(
            test_data,
            recency_days=30,  # Include all by recency
            min_duration=40,
            max_duration=50
        )
        
        # Should only include video2 (45 seconds)
        assert len(filtered) == 1
        assert filtered[0]["video_id"] == "test_video_2"
    
    def test_remove_duplicates(self, searcher):
        """Test duplicate removal"""
        duplicate_data = [
            {"video_id": "video1", "title": "First"},
            {"video_id": "video2", "title": "Second"},
            {"video_id": "video1", "title": "Duplicate"},  # Duplicate
            {"video_id": "video3", "title": "Third"},
        ]
        
        unique = searcher._remove_duplicates(duplicate_data)
        
        assert len(unique) == 3
        video_ids = [v["video_id"] for v in unique]
        assert video_ids == ["video1", "video2", "video3"]
    
    def test_is_vietnamese_content(self, searcher):
        """Test Vietnamese content detection"""
        vietnamese_video = {"title": "Video về Việt Nam"}
        english_video = {"title": "English video"}
        
        assert searcher._is_vietnamese_content(vietnamese_video) is True
        assert searcher._is_vietnamese_content(english_video) is False
    
    @pytest.mark.asyncio
    async def test_search_vietnamese_content(self, searcher, mock_video_data):
        """Test Vietnamese-specific content search"""
        with patch.object(searcher, 'search_videos_by_keywords') as mock_search:
            mock_search.return_value = mock_video_data
            
            results = await searcher.search_vietnamese_content(
                queries=["test"],
                recency_days=7,
                num_videos=5
            )
            
            # Should call with enhanced queries including Vietnamese terms
            mock_search.assert_called_once()
            called_queries = mock_search.call_args[0][0]
            assert "test vietnam" in called_queries
            assert "test việt nam" in called_queries
    
    @pytest.mark.asyncio
    async def test_search_with_empty_queries(self, searcher):
        """Test search with empty query list"""
        results = await searcher.search_videos_by_keywords(
            queries=[],
            recency_days=7,
            num_videos=10
        )
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_search_with_api_error(self, searcher):
        """Test search when API client raises exception"""
        with patch('platform_crawler.tiktok.tiktok_searcher.TikTokApiClient') as mock_client:
            # Mock the context manager to raise an exception
            mock_instance = AsyncMock()
            mock_instance.__aenter__.side_effect = Exception("API error")
            mock_client.return_value = mock_instance
            
            results = await searcher.search_videos_by_keywords(
                queries=["test"],
                recency_days=7,
                num_videos=10
            )
            
            assert results == []
    
    @pytest.mark.asyncio
    async def test_search_by_keyword_internal(self, searcher):
        """Test internal keyword search method"""
        mock_api_client = AsyncMock()
        mock_api_client.search_videos.return_value = [{"video_id": "test"}]
        searcher.api_client = mock_api_client
        
        results = await searcher._search_by_keyword("test", 5)
        
        assert len(results) == 1
        assert results[0]["video_id"] == "test"
        mock_api_client.search_videos.assert_called_once_with("test", 5)
    
    @pytest.mark.asyncio
    async def test_search_by_keyword_no_client(self, searcher):
        """Test internal keyword search without API client"""
        searcher.api_client = None
        
        results = await searcher._search_by_keyword("test", 5)
        
        assert results == []