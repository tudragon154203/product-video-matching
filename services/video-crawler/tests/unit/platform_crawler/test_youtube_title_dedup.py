"""
Unit tests for YouTube crawler title-based deduplication.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from platform_crawler.youtube.youtube_crawler import YoutubeCrawler


class TestYoutubeTitleDeduplication:
    """Test cases for YouTube-specific title deduplication."""

    def test_youtube_crawler_enables_title_deduplication(self):
        """Test that YouTube crawler enables title deduplication by default."""
        with patch('platform_crawler.youtube.youtube_searcher.YoutubeSearcher'), \
             patch('platform_crawler.youtube.downloader.YoutubeDownloader'):
            crawler = YoutubeCrawler()
            assert crawler._enable_title_deduplication is True
            assert crawler._dedupe_key == "video_id"

    def test_youtube_deduplicate_uses_title_field(self):
        """Test that YouTube deduplication uses title field."""
        with patch('platform_crawler.youtube.youtube_searcher.YoutubeSearcher'), \
             patch('platform_crawler.youtube.downloader.YoutubeDownloader'):
            crawler = YoutubeCrawler()

            videos = [
                {"video_id": "yt1", "title": "Product Review"},
                {"video_id": "yt2", "title": "Product Review"},  # Duplicate title
                {"video_id": "yt3", "title": "Different Video"},
                {"video_id": "yt4", "title": None},  # No title
            ]

            result = crawler._deduplicate_videos(videos)

            # Should deduplicate by title
            assert len(result) == 3  # yt2 should be deduplicated
            titles = [video.get("title") for video in result.values()]
            assert "Product Review" in titles
            assert "Different Video" in titles
            assert None in titles

    def test_youtube_deduplicate_with_title_disabled(self):
        """Test YouTube deduplication when title deduplication is disabled."""
        with patch('platform_crawler.youtube.youtube_searcher.YoutubeSearcher'), \
             patch('platform_crawler.youtube.downloader.YoutubeDownloader'):
            # Create crawler with title deduplication disabled
            crawler = YoutubeCrawler()
            crawler._enable_title_deduplication = False

            videos = [
                {"video_id": "yt1", "title": "Same Title"},
                {"video_id": "yt2", "title": "Same Title"},  # Should not be deduplicated
                {"video_id": "yt3", "title": "Different Title"},
            ]

            result = crawler._deduplicate_videos(videos)

            # Should have all 3 videos (only ID deduplication)
            assert len(result) == 3

    def test_youtube_deduplicate_id_takes_precedence(self):
        """Test that ID deduplication takes precedence over title deduplication."""
        with patch('platform_crawler.youtube.youtube_searcher.YoutubeSearcher'), \
             patch('platform_crawler.youtube.downloader.YoutubeDownloader'):
            crawler = YoutubeCrawler()

            videos = [
                {"video_id": "same_id", "title": "Title 1"},
                {"video_id": "same_id", "title": "Title 2"},  # Same ID, different title
                {"video_id": "different_id", "title": "Title 1"},  # Different ID, same title
            ]

            result = crawler._deduplicate_videos(videos)

            # Should have 1 video (ID deduplication first, then title deduplication)
            assert len(result) == 1
            assert result["video_0"]["video_id"] == "same_id"
            assert result["video_0"]["title"] == "Title 1"

    def test_youtube_deduplicate_empty_and_none_titles(self):
        """Test YouTube deduplication with empty and None titles."""
        with patch('platform_crawler.youtube.youtube_searcher.YoutubeSearcher'), \
             patch('platform_crawler.youtube.downloader.YoutubeDownloader'):
            crawler = YoutubeCrawler()

            videos = [
                {"video_id": "yt1", "title": None},
                {"video_id": "yt2", "title": None},
                {"video_id": "yt3", "title": ""},
                {"video_id": "yt4", "title": ""},
                {"video_id": "yt5", "title": "Valid Title"},
                {"video_id": "yt6", "title": "Valid Title"},  # Should be deduplicated
            ]

            result = crawler._deduplicate_videos(videos)

            # None and empty titles should not be deduplicated, valid titles should
            assert len(result) == 5

    def test_youtube_deduplicate_title_whitespace(self):
        """Test that title whitespace is handled correctly."""
        with patch('platform_crawler.youtube.youtube_searcher.YoutubeSearcher'), \
             patch('platform_crawler.youtube.downloader.YoutubeDownloader'):
            crawler = YoutubeCrawler()

            videos = [
                {"video_id": "yt1", "title": "Product Review"},
                {"video_id": "yt2", "title": "  Product Review  "},  # Same title with whitespace
                {"video_id": "yt3", "title": "Product Review "},
            ]

            result = crawler._deduplicate_videos(videos)

            # Should treat titles with different whitespace as duplicates
            assert len(result) == 1
            assert result["video_0"]["video_id"] == "yt1"

    def test_youtube_deduplicate_case_sensitive(self):
        """Test that YouTube title deduplication is case-sensitive."""
        with patch('platform_crawler.youtube.youtube_searcher.YoutubeSearcher'), \
             patch('platform_crawler.youtube.downloader.YoutubeDownloader'):
            crawler = YoutubeCrawler()

            videos = [
                {"video_id": "yt1", "title": "Product Review"},
                {"video_id": "yt2", "title": "product review"},  # Different case
                {"video_id": "yt3", "title": "Product Review"},  # Exact match
            ]

            result = crawler._deduplicate_videos(videos)

            # Should treat different cases as different titles
            assert len(result) == 2
            assert result["video_0"]["video_id"] == "yt1"
            assert result["video_1"]["video_id"] == "yt2"

    @pytest.mark.asyncio
    async def test_youtube_integration_title_deduplication(self):
        """Test full integration of title deduplication in YouTube crawler."""
        mock_searcher = Mock()
        mock_searcher.search_youtube = AsyncMock(return_value=[
            {"video_id": "yt1", "title": "Same Title", "url": "url1"},
            {"video_id": "yt2", "title": "Same Title", "url": "url2"},
            {"video_id": "yt3", "title": "Different Title", "url": "url3"},
        ])

        mock_downloader = Mock()
        mock_downloader.download_video = AsyncMock(side_effect=[
            {"video_id": "yt1", "title": "Same Title", "local_path": "/path/yt1.mp4"},
            {"video_id": "yt3", "title": "Different Title", "local_path": "/path/yt3.mp4"},
        ])

        with patch('platform_crawler.youtube.youtube_searcher.YoutubeSearcher', return_value=mock_searcher), \
             patch('platform_crawler.youtube.downloader.YoutubeDownloader', return_value=mock_downloader), \
             patch('platform_crawler.youtube.youtube_crawler.config'), \
             patch('asyncio.Semaphore'), \
             patch('asyncio.gather', return_value=[{"video_id": "yt1"}, {"video_id": "yt3"}]):

            crawler = YoutubeCrawler()
            result = await crawler._search_videos_for_queries(["test"], 30, 10)

            # Should return 3 videos from search (before deduplication)
            assert len(result) == 3

            # Test deduplication directly
            deduplicated = crawler._deduplicate_videos(result)
            assert len(deduplicated) == 2  # One duplicate title removed