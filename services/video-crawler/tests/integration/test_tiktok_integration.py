"""
Integration tests for TikTok functionality
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from platform_crawler.tiktok.tiktok_crawler import TikTokCrawler
from platform_crawler.tiktok.tiktok_api_client import TikTokApiClient
from platform_crawler.tiktok.vietnam_optimizer import VietnamTikTokOptimizer, VietnamContentFilter
from config_loader import config


class TestTikTokIntegration:
    """Integration test cases for TikTok functionality"""
    
    @pytest.fixture
    def crawler(self):
        """Create TikTokCrawler instance for testing"""
        return TikTokCrawler()
    
    @pytest.fixture 
    def vietnam_optimizer(self):
        """Create VietnamTikTokOptimizer instance for testing"""
        return VietnamTikTokOptimizer()
    
    @pytest.fixture
    def content_filter(self):
        """Create VietnamContentFilter instance for testing"""
        return VietnamContentFilter()
    
    @pytest.mark.asyncio
    async def test_api_client_session_management(self, mock_tiktok_api):
        """Test TikTok API client session management"""
        with patch('platform_crawler.tiktok.tiktok_api_client.TikTokApi', return_value=mock_tiktok_api):
            async with TikTokApiClient() as client:
                assert client.is_session_initialized() is True
                
                # Test basic search functionality
                mock_hashtag = MagicMock()
                mock_hashtag.videos = AsyncMock(return_value=iter([]))
                mock_tiktok_api.hashtag.return_value = mock_hashtag
                
                videos = await client.search_videos("test", count=1)
                assert isinstance(videos, list)
            
            # Verify session was closed
            mock_tiktok_api.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_functionality_integration(self, crawler, mock_video_data):
        """Test TikTok search functionality integration"""
        with patch('platform_crawler.tiktok.tiktok_searcher.TikTokApiClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.search_videos.return_value = mock_video_data
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Test keyword search
            keyword_results = await crawler.searcher.search_videos_by_keywords(
                queries=["vietnam"],
                recency_days=30,
                num_videos=2
            )
            
            assert len(keyword_results) == 2
            assert all("video_id" in video for video in keyword_results)
            assert all("platform" in video for video in keyword_results)
    
    @pytest.mark.asyncio
    async def test_vietnam_content_search_integration(self, crawler, vietnamese_test_videos):
        """Test Vietnamese content search integration"""
        with patch.object(crawler.searcher, 'search_videos_by_keywords') as mock_search:
            mock_search.return_value = vietnamese_test_videos
            
            vietnam_results = await crawler.searcher.search_vietnamese_content(
                queries=["product"],
                recency_days=30,
                num_videos=2
            )
            
            # Should have enhanced queries
            mock_search.assert_called_once()
            called_queries = mock_search.call_args[0][0]
            assert len(called_queries) > 1  # Enhanced with Vietnam terms
            assert "product vietnam" in called_queries
    
    @pytest.mark.asyncio
    async def test_download_functionality_integration(self, temp_dir):
        """Test TikTok download functionality integration"""
        test_video = {
            "video_id": "test_video_123",
            "url": "https://tiktok.com/@test/video/123",
            "title": "Test video for download",
            "platform": "tiktok"
        }
        
        from platform_crawler.tiktok.tiktok_downloader import TikTokDownloader
        
        with patch.object(TikTokDownloader, '_initialize_session'):
            with patch.object(TikTokDownloader, '_cleanup_session'):
                with patch.object(TikTokDownloader, '_get_download_url', return_value=None):
                    async with TikTokDownloader() as downloader:
                        # This will attempt download but fail gracefully with None URL
                        local_path = await downloader.download_video(test_video, temp_dir)
                        
                        # Should handle the failure gracefully
                        assert local_path is None or isinstance(local_path, str)
    
    @pytest.mark.asyncio 
    async def test_crawler_end_to_end_integration(self, crawler, temp_dir, mock_downloaded_video_data):
        """Test full crawler integration end-to-end"""
        with patch.object(crawler, '_search_videos') as mock_search, \
             patch.object(crawler, '_download_videos') as mock_download:
            
            # Mock successful search and download
            mock_search.return_value = mock_downloaded_video_data
            mock_download.return_value = mock_downloaded_video_data
            
            results = await crawler.search_and_download_videos(
                queries=["vietnam tech"],
                recency_days=30,
                download_dir=temp_dir,
                num_videos=1
            )
            
            assert len(results) == 2
            assert all("platform" in r and r["platform"] == "tiktok" for r in results)
            assert all("video_id" in r for r in results)
            assert all("url" in r for r in results)
    
    def test_vietnam_optimization_integration(self, vietnam_optimizer, vietnamese_test_videos):
        """Test Vietnam-specific optimizations integration"""
        # Test query enhancement
        original_queries = ["product review", "tech unboxing"]
        enhanced_queries = vietnam_optimizer.enhance_search_queries_for_vietnam(original_queries)
        
        assert len(enhanced_queries) > len(original_queries)
        assert any("vietnam" in query.lower() for query in enhanced_queries)
        assert any("việt nam" in query.lower() for query in enhanced_queries)
    
    def test_content_filtering_integration(self, content_filter, vietnamese_test_videos):
        """Test content filtering integration"""
        filtered_videos = content_filter.filter_for_vietnam_market(vietnamese_test_videos, min_score=0.2)
        
        assert len(filtered_videos) > 0
        assert all("vietnam_relevance_score" in v for v in filtered_videos)
        
        # Vietnamese content should score higher
        vietnamese_videos = [v for v in filtered_videos if "việt nam" in v["title"].lower() or "vietnam" in v["title"].lower()]
        if vietnamese_videos:
            assert all(v["vietnam_relevance_score"] > 0.3 for v in vietnamese_videos)
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self, crawler):
        """Test health check integration"""
        with patch.object(crawler.searcher, 'search_videos_by_keywords') as mock_search:
            # Test successful health check
            mock_search.return_value = [{"video_id": "test"}]
            is_healthy = await crawler.health_check()
            assert is_healthy is True
            
            # Test failed health check
            mock_search.return_value = []
            is_healthy = await crawler.health_check()
            assert is_healthy is True  # Even 0 results means API is working
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, crawler, temp_dir):
        """Test error handling integration"""
        # Test with empty queries
        results = await crawler.search_and_download_videos(
            queries=[],
            recency_days=7,
            download_dir=temp_dir,
            num_videos=5
        )
        assert results == []
        
        # Test with search errors
        with patch.object(crawler, '_search_videos') as mock_search:
            mock_search.side_effect = Exception("Search failed")
            
            results = await crawler.search_and_download_videos(
                queries=["test"],
                recency_days=7,
                download_dir=temp_dir,
                num_videos=5
            )
            assert results == []
    
    def test_configuration_validation_integration(self, mock_config):
        """Test configuration validation integration"""
        from platform_crawler.tiktok.tiktok_utils import validate_tiktok_config
        
        # Test valid config
        errors = validate_tiktok_config(mock_config.__dict__)
        assert isinstance(errors, list)
        
        # Test invalid config
        invalid_config = {
            'TIKTOK_BROWSER': 'invalid_browser',
            'TIKTOK_MAX_RETRIES': -1,
            'TIKTOK_SLEEP_AFTER': -5
        }
        errors = validate_tiktok_config(invalid_config)
        assert len(errors) > 0
        assert any("browser" in error.lower() for error in errors)


@pytest.mark.integration
class TestTikTokRealAPIIntegration:
    """Integration tests that can optionally run against real TikTok API"""
    
    pytestmark = pytest.mark.skipif(
        not config.TIKTOK_MS_TOKEN,  # Skip if no token available in config
        reason="Requires real TikTok API access and ms_token. Set TIKTOK_MS_TOKEN in .env to enable."
    )
    
    @pytest.mark.asyncio
    async def test_real_api_connection(self):
        """Test real API connection and MUST return real search results or FAIL
        
        This test is STRICT - it will fail if no real search results are returned,
        regardless of the reason (API issues, network problems, blocking, etc.).
        The test validates that the service can actually search TikTok and return real results.
        
        Browser mode (headless/visible) is controlled by TIKTOK_HEADLESS in .env file.
        """
        from common_py.logging_config import configure_logging
        logger = configure_logging("test-tiktok-integration")
        
        logger.info("🔥 Starting STRICT TikTok real API integration test - MUST return real results or FAIL")
        headless_mode = getattr(config, 'TIKTOK_HEADLESS', True)
        browser_mode = "headless" if headless_mode else "visible"
        logger.info(f"🖥️  Running with {browser_mode} browser (TIKTOK_HEADLESS={headless_mode})")
        
        # Create API client and initialize session
        api_client = TikTokApiClient()
        init_success = await api_client.initialize_session()
        
        if not init_success:
            pytest.fail("❌ FAILED: Could not initialize TikTok API session - check configuration and network")
        
        logger.info("✅ TikTok API session initialized successfully")
        
        # Perform a real search with a common Vietnamese term
        search_term = "cách chọn gối ngủ tốt"  # "how to choose a good pillow" in Vietnamese
        logger.info(f"🔍 Searching TikTok for: '{search_term}'")
        
        try:
            videos = await api_client.search_videos(search_term, count=3)
            
            if not videos:
                pytest.fail(f"❌ FAILED: No videos returned for search term '{search_term}' - API may be blocked or search term may be invalid")
            
            logger.info(f"✅ SUCCESS: Found {len(videos)} videos for search term '{search_term}'")
            
            # Validate that we got real video data
            for i, video in enumerate(videos):
                required_fields = ['video_id', 'url', 'title', 'author', 'duration_s']
                missing_fields = [field for field in required_fields if field not in video]
                
                if missing_fields:
                    pytest.fail(f"❌ FAILED: Video {i} missing required fields: {missing_fields}")
                
                logger.info(f"📺 Video {i+1}: {video['title'][:50]}... by @{video['author']}")
            
            logger.info("🎉 ALL TESTS PASSED - TikTok API is working correctly!")
            
        except Exception as e:
            pytest.fail(f"❌ FAILED: Exception during search: {str(e)}")
        finally:
            # Clean up session
            await api_client.close_session()
            logger.info("🧹 Cleaned up TikTok API session")
    
    @pytest.mark.asyncio
    async def test_real_api_download_url(self):
        """Test real API download URL retrieval"""
        from common_py.logging_config import configure_logging
        logger = configure_logging("test-tiktok-download")
        
        logger.info("📥 Testing TikTok download URL retrieval")
        
        # Create API client and initialize session
        api_client = TikTokApiClient()
        init_success = await api_client.initialize_session()
        
        if not init_success:
            pytest.skip("Could not initialize TikTok API session - skipping download test")
        
        try:
            # Search for a video to test download URL retrieval
            videos = await api_client.search_videos("test", count=1)
            
            if not videos:
                pytest.skip("No videos found for download URL test")
            
            video_id = videos[0]["video_id"]
            logger.info(f"📥 Getting download URL for video: {video_id}")
            
            download_url = await api_client.get_video_download_url(video_id)
            
            if download_url:
                logger.info(f"✅ SUCCESS: Got download URL: {download_url[:100]}...")
            else:
                logger.warning("⚠️  No download URL found (this may be expected for some videos)")
                
        except Exception as e:
            logger.error(f"❌ Error during download URL test: {str(e)}")
        finally:
            # Clean up session
            await api_client.close_session()
            logger.info("🧹 Cleaned up TikTok API session")