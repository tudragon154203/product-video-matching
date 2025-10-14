"""
Unit tests for TikTok crawler title-based deduplication.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from platform_crawler.tiktok.tiktok_crawler import TikTokCrawler


class TestTikTokTitleDeduplication:
    """Test cases for TikTok-specific title deduplication."""

    def test_tiktok_crawler_enables_title_deduplication(self):
        """Test that TikTok crawler enables title deduplication by default."""
        with patch('platform_crawler.tiktok.tiktok_searcher.TikTokSearcher'), \
             patch('platform_crawler.tiktok.tiktok_downloader.TikTokDownloader'):
            crawler = TikTokCrawler()
            assert crawler._enable_title_deduplication is True
            assert crawler._dedupe_key == "id"

    def test_tiktok_deduplicate_uses_caption_field(self):
        """Test that TikTok deduplication uses caption field for titles."""
        with patch('platform_crawler.tiktok.tiktok_searcher.TikTokSearcher'), \
             patch('platform_crawler.tiktok.tiktok_downloader.TikTokDownloader'):
            crawler = TikTokCrawler()

            videos = [
                {"id": "tiktok1", "caption": "Cool Product"},
                {"id": "tiktok2", "caption": "Cool Product"},  # Duplicate caption
                {"id": "tiktok3", "caption": "Different Product"},
                {"id": "tiktok4", "caption": None},  # No caption
            ]

            result = crawler._deduplicate_videos(videos)

            # Should deduplicate by caption, not title
            assert len(result) == 3  # tiktok2 should be deduplicated
            captions = [video.get("caption") for video in result.values()]
            assert "Cool Product" in captions
            assert "Different Product" in captions
            assert None in captions

    def test_tiktok_deduplicate_with_title_disabled(self):
        """Test TikTok deduplication when title deduplication is disabled."""
        with patch('platform_crawler.tiktok.tiktok_searcher.TikTokSearcher'), \
             patch('platform_crawler.tiktok.tiktok_downloader.TikTokDownloader'):
            # Create crawler with title deduplication disabled
            crawler = TikTokCrawler()
            crawler._enable_title_deduplication = False

            videos = [
                {"id": "tiktok1", "caption": "Same Caption"},
                {"id": "tiktok2", "caption": "Same Caption"},  # Should not be deduplicated
                {"id": "tiktok3", "caption": "Different Caption"},
            ]

            result = crawler._deduplicate_videos(videos)

            # Should have all 3 videos (only ID deduplication)
            assert len(result) == 3

    def test_tiktok_deduplicate_id_takes_precedence(self):
        """Test that ID deduplication takes precedence over caption deduplication."""
        with patch('platform_crawler.tiktok.tiktok_searcher.TikTokSearcher'), \
             patch('platform_crawler.tiktok.tiktok_downloader.TikTokDownloader'):
            crawler = TikTokCrawler()

            videos = [
                {"id": "same_id", "caption": "Caption 1"},
                {"id": "same_id", "caption": "Caption 2"},  # Same ID, different caption
                {"id": "different_id", "caption": "Caption 1"},  # Different ID, same caption
            ]

            result = crawler._deduplicate_videos(videos)

            # Should have 1 video (ID deduplication first, then caption deduplication)
            assert len(result) == 1
            assert result["video_0"]["id"] == "same_id"
            assert result["video_0"]["caption"] == "Caption 1"

    def test_tiktok_deduplicate_empty_and_none_captions(self):
        """Test TikTok deduplication with empty and None captions."""
        with patch('platform_crawler.tiktok.tiktok_searcher.TikTokSearcher'), \
             patch('platform_crawler.tiktok.tiktok_downloader.TikTokDownloader'):
            crawler = TikTokCrawler()

            videos = [
                {"id": "tiktok1", "caption": None},
                {"id": "tiktok2", "caption": None},
                {"id": "tiktok3", "caption": ""},
                {"id": "tiktok4", "caption": ""},
                {"id": "tiktok5", "caption": "Valid Caption"},
                {"id": "tiktok6", "caption": "Valid Caption"},  # Should be deduplicated
            ]

            result = crawler._deduplicate_videos(videos)

            # None and empty captions should not be deduplicated, valid captions should
            assert len(result) == 5

    def test_tiktok_deduplicate_caption_whitespace(self):
        """Test that caption whitespace is handled correctly."""
        with patch('platform_crawler.tiktok.tiktok_searcher.TikTokSearcher'), \
             patch('platform_crawler.tiktok.tiktok_downloader.TikTokDownloader'):
            crawler = TikTokCrawler()

            videos = [
                {"id": "tiktok1", "caption": "Product Review"},
                {"id": "tiktok2", "caption": "  Product Review  "},  # Same caption with whitespace
                {"id": "tiktok3", "caption": "Product Review "},
            ]

            result = crawler._deduplicate_videos(videos)

            # Should treat captions with different whitespace as duplicates
            assert len(result) == 1
            assert result["video_0"]["id"] == "tiktok1"

    @pytest.mark.asyncio
    async def test_tiktok_integration_title_deduplication(self):
        """Test full integration of title deduplication in TikTok crawler."""
        mock_searcher = Mock()
        mock_searcher.search_tiktok = AsyncMock(return_value=Mock(
            results=[
                Mock(id="tiktok1", caption="Same Caption", author_handle="user1",
                     like_count=100, upload_time="2023-01-01", web_view_url="url1"),
                Mock(id="tiktok2", caption="Same Caption", author_handle="user2",
                     like_count=200, upload_time="2023-01-02", web_view_url="url2"),
                Mock(id="tiktok3", caption="Different Caption", author_handle="user3",
                     like_count=150, upload_time="2023-01-03", web_view_url="url3"),
            ]
        ))

        mock_downloader = Mock()
        mock_downloader.download_videos_batch = AsyncMock(return_value=[
            {"id": "tiktok1", "caption": "Same Caption", "local_path": "/path/tiktok1.mp4"},
            {"id": "tiktok3", "caption": "Different Caption", "local_path": "/path/tiktok3.mp4"},
        ])

        with patch('platform_crawler.tiktok.tiktok_searcher.TikTokSearcher', return_value=mock_searcher), \
             patch('platform_crawler.tiktok.tiktok_downloader.TikTokDownloader', return_value=mock_downloader), \
             patch('platform_crawler.tiktok.tiktok_crawler.config'):

            crawler = TikTokCrawler()
            result = await crawler._search_videos_for_queries(["test"], 30, 10)

            # Should return 3 videos from search (before deduplication)
            assert len(result) == 3

            # Test deduplication directly
            deduplicated = crawler._deduplicate_videos(result)
            assert len(deduplicated) == 2  # One duplicate caption removed