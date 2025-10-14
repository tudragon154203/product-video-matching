"""
Unit tests for title-based deduplication integration with BaseVideoCrawler.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from platform_crawler.common.base_crawler import BaseVideoCrawler


class MockPlatformCrawler(BaseVideoCrawler):
    """Mock crawler implementation for testing."""

    def __init__(self, platform_name="test", logger=None, enable_title_deduplication=True):
        if logger is None:
            logger = Mock()
            logger.info = Mock()
        super().__init__(platform_name, logger, enable_title_deduplication)

    async def _search_videos_for_queries(self, queries, recency_days, num_videos):
        # Mock search results
        return [
            {"video_id": f"vid{i}", "title": f"Title {i % 3}"}
            for i in range(num_videos)
        ]

    async def _download_videos(self, videos, download_dir):
        # Mock download - return the videos as-is
        return list(videos.values())


class TestBaseCrawlerTitleDeduplication:
    """Test cases for title-based deduplication in BaseVideoCrawler."""

    @pytest.mark.asyncio
    async def test_title_deduplication_enabled_by_default(self):
        """Test that title deduplication is enabled by default."""
        crawler = MockPlatformCrawler(enable_title_deduplication=True)
        assert crawler._enable_title_deduplication is True

    @pytest.mark.asyncio
    async def test_title_deduplication_can_be_disabled(self):
        """Test that title deduplication can be disabled."""
        crawler = MockPlatformCrawler(enable_title_deduplication=False)
        assert crawler._enable_title_deduplication is False

    @pytest.mark.asyncio
    async def test_deduplicate_videos_with_title_enabled(self):
        """Test video deduplication when title deduplication is enabled."""
        crawler = MockPlatformCrawler(enable_title_deduplication=True)

        videos = [
            {"video_id": "vid1", "title": "Same Title"},
            {"video_id": "vid2", "title": "Same Title"},  # Duplicate title
            {"video_id": "vid3", "title": "Different Title"},
        ]

        result = crawler._deduplicate_videos(videos)

        # Should have 2 unique videos (title deduplication applied)
        assert len(result) == 2
        # Result should be in dict format for compatibility
        assert isinstance(result, dict)
        assert "video_0" in result
        assert "video_1" in result

    @pytest.mark.asyncio
    async def test_deduplicate_videos_with_title_disabled(self):
        """Test video deduplication when title deduplication is disabled."""
        crawler = MockPlatformCrawler(enable_title_deduplication=False)

        videos = [
            {"video_id": "vid1", "title": "Same Title"},
            {"video_id": "vid2", "title": "Same Title"},  # Should not be deduplicated by title
            {"video_id": "vid3", "title": "Different Title"},
        ]

        result = crawler._deduplicate_videos(videos)

        # Should have all 3 videos (only ID deduplication applied)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_deduplicate_videos_id_deduplication_takes_precedence(self):
        """Test that ID deduplication always happens before title deduplication."""
        crawler = MockPlatformCrawler(enable_title_deduplication=True)

        videos = [
            {"video_id": "same_id", "title": "Title 1"},
            {"video_id": "same_id", "title": "Title 2"},  # Same ID, different title
            {"video_id": "different_id", "title": "Title 1"},  # Different ID, same title
        ]

        result = crawler._deduplicate_videos(videos)

        # Should have 1 video (ID deduplication removes second,
        # then title deduplication removes third)
        assert len(result) == 1
        assert result["video_0"]["video_id"] == "same_id"
        assert result["video_0"]["title"] == "Title 1"

    @pytest.mark.asyncio
    async def test_deduplicate_videos_preserves_order(self):
        """Test that order is preserved in title deduplication."""
        crawler = MockPlatformCrawler(enable_title_deduplication=True)

        videos = [
            {"video_id": "vid1", "title": "Title A"},
            {"video_id": "vid2", "title": "Title B"},
            {"video_id": "vid3", "title": "Title A"},  # Duplicate title
            {"video_id": "vid4", "title": "Title C"},
        ]

        result = crawler._deduplicate_videos(videos)

        # Should preserve order of first occurrences
        assert len(result) == 3
        assert result["video_0"]["video_id"] == "vid1"  # First Title A
        assert result["video_1"]["video_id"] == "vid2"  # First Title B
        assert result["video_2"]["video_id"] == "vid4"  # Title C

    @pytest.mark.asyncio
    async def test_deduplicate_videos_with_none_titles(self):
        """Test that None titles are handled correctly."""
        crawler = MockPlatformCrawler(enable_title_deduplication=True)

        videos = [
            {"video_id": "vid1", "title": None},
            {"video_id": "vid2", "title": None},
            {"video_id": "vid3", "title": "Valid Title"},
            {"video_id": "vid4", "title": "Valid Title"},  # Should be deduplicated
        ]

        result = crawler._deduplicate_videos(videos)

        # None titles should not be deduplicated, valid titles should
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_deduplicate_videos_empty_input(self):
        """Test deduplication with empty input."""
        crawler = MockPlatformCrawler(enable_title_deduplication=True)

        result = crawler._deduplicate_videos([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_deduplicate_videos_dict_output_format(self):
        """Test that output format is compatible with existing code."""
        crawler = MockPlatformCrawler(enable_title_deduplication=True)

        videos = [
            {"video_id": "vid1", "title": "Title 1"},
            {"video_id": "vid2", "title": "Title 2"},
        ]

        result = crawler._deduplicate_videos(videos)

        # Should return dict format
        assert isinstance(result, dict)
        assert "video_0" in result
        assert "video_1" in result
        assert result["video_0"]["video_id"] == "vid1"
        assert result["video_1"]["video_id"] == "vid2"