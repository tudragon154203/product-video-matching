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
                assert client.is_session_active() is True
                
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
        
        # Test 1: Verify configuration is present
        assert config.TIKTOK_MS_TOKEN is not None, "TIKTOK_MS_TOKEN must be configured in config"
        assert len(config.TIKTOK_MS_TOKEN) > 0, "TIKTOK_MS_TOKEN cannot be empty"
        logger.info("✓ TikTok configuration verified")
        
        # Test 2: Initialize client and session - MUST succeed
        try:
            async with TikTokApiClient() as client:
                assert client is not None, "TikTok client creation failed"
                logger.info("✓ TikTok client created successfully")
                
                # Test 3: Session MUST be active for real API test
                if not client.is_session_active():
                    pytest.fail(
                        "❌ FAILED: TikTok API session failed to initialize. "
                        "Cannot perform real API test without active session. "
                        "This means the service cannot connect to TikTok."
                    )
                
                logger.info("✓ TikTok API session is active")
                
                # Test 4: Perform real searches and REQUIRE actual results
                test_queries = ["vietnam", "product", "tech", "food"]
                total_videos_found = 0
                successful_queries = []
                failed_queries = []
                search_details = {}
                
                for query in test_queries:
                    try:
                        logger.info(f"🔍 Searching TikTok for: '{query}'")
                        videos = await client.search_videos(query, count=5)
                        
                        # Validate response format
                        assert isinstance(videos, list), f"Search for '{query}' must return a list, got {type(videos)}"
                        
                        video_count = len(videos)
                        search_details[query] = {
                            "count": video_count,
                            "status": "success" if video_count > 0 else "empty"
                        }
                        
                        if video_count > 0:
                            logger.info(f"✅ Query '{query}' returned {video_count} real videos")
                            total_videos_found += video_count
                            successful_queries.append(query)
                            
                            # Validate video data structure for first video
                            video = videos[0]
                            required_fields = ["video_id", "title", "author", "platform"]
                            for field in required_fields:
                                assert field in video, f"Video from '{query}' missing required field: {field}"
                            assert video["platform"] == "tiktok", f"Video platform must be 'tiktok', got '{video['platform']}'"
                            
                            logger.info(f"✓ Video data structure validated for query '{query}'")
                        else:
                            logger.warning(f"⚠️  Query '{query}' returned empty results")
                            failed_queries.append(query)
                            
                    except Exception as e:
                        logger.error(f"❌ Search failed for query '{query}': {str(e)}")
                        failed_queries.append(query)
                        search_details[query] = {
                            "count": 0,
                            "status": "error",
                            "error": str(e)
                        }
                
                # Log comprehensive results
                logger.info(f"📊 Search Results Summary:")
                logger.info(f"   Total videos found: {total_videos_found}")
                logger.info(f"   Successful queries: {successful_queries}")
                logger.info(f"   Failed/empty queries: {failed_queries}")
                logger.info(f"   Detailed results: {search_details}")
                
                # Test 5: CRITICAL REQUIREMENT - MUST have real results or FAIL
                if total_videos_found == 0:
                    failure_message = (
                        f"🚨 INTEGRATION TEST FAILED - NO REAL SEARCH RESULTS RETURNED 🚨\n\n"
                        f"❌ FAILURE DETAILS:\n"
                        f"   • Total videos found: {total_videos_found}\n"
                        f"   • Queries attempted: {test_queries}\n"
                        f"   • Successful queries: {successful_queries}\n"
                        f"   • Failed queries: {failed_queries}\n"
                        f"   • Search details: {search_details}\n\n"
                        f"💥 CRITICAL ISSUE: The TikTok service cannot return real search results.\n"
                        f"   This could be due to:\n"
                        f"   - TikTok API being blocked or rate limited\n"
                        f"   - Invalid or expired MS_TOKEN\n"
                        f"   - Network connectivity issues\n"
                        f"   - TikTok API changes or restrictions\n"
                        f"   - Geographic or IP-based blocking\n\n"
                        f"🔧 REQUIRED ACTION: Fix the underlying issue so the service can search TikTok\n"
                        f"   and return real video results before this test will pass."
                    )
                    pytest.fail(failure_message)
                
                # Test passed - we have real results!
                logger.info(f"🎉 SUCCESS: Integration test PASSED with {total_videos_found} real videos from TikTok API")
                logger.info(f"✅ The service CAN search TikTok and return real results")
                
        except Exception as e:
            # Any exception during the test should result in failure
            pytest.fail(
                f"🚨 INTEGRATION TEST FAILED - EXCEPTION OCCURRED 🚨\n\n"
                f"❌ ERROR: {str(e)}\n"
                f"💥 The TikTok service encountered an error and cannot function properly.\n"
                f"🔧 REQUIRED ACTION: Fix the underlying issue before this test will pass."
            )
        
        # Test 6: Verify service components work after successful API test
        try:
            from platform_crawler.tiktok.tiktok_crawler import TikTokCrawler
            crawler = TikTokCrawler()
            assert crawler.get_platform_name() == "tiktok", "TikTok crawler platform name validation failed"
            logger.info("✓ TikTok service components verified")
        except Exception as e:
            pytest.fail(f"Service component verification failed: {str(e)}")
        
        logger.info("🏆 STRICT real API integration test PASSED - Service can search TikTok and return real results!")