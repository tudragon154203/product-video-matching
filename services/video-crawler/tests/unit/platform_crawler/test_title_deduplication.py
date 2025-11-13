"""
Unit tests for title-based video deduplication logic.
"""

# Unused import removed: pytest
from platform_crawler.common.utils import deduplicate_videos_by_id_and_title


class TestVideoTitleDeduplication:
    """Test cases for title-based video deduplication."""

    def test_deduplicate_by_id_and_title_basic(self):
        """Test basic title-based deduplication functionality."""
        videos = [
            {"video_id": "vid1", "title": "Amazing Product Review"},
            {"video_id": "vid2", "title": "Amazing Product Review"},  # Duplicate title
            {"video_id": "vid3", "title": "Different Video"},
        ]

        result = deduplicate_videos_by_id_and_title(videos)

        # Should keep only first video with duplicate title
        assert len(result) == 2
        assert result[0]["video_id"] == "vid1"
        assert result[1]["video_id"] == "vid3"
        assert result[0]["title"] == "Amazing Product Review"
        assert result[1]["title"] == "Different Video"

    def test_deduplicate_by_id_first_then_title(self):
        """Test that ID deduplication takes precedence over title deduplication."""
        videos = [
            {"video_id": "vid1", "title": "First Video"},
            {"video_id": "vid1", "title": "First Video Duplicate ID"},  # Same ID
            {"video_id": "vid2", "title": "First Video"},  # Same title, different ID
        ]

        result = deduplicate_videos_by_id_and_title(videos)

        # Should keep only first video (ID deduplication removes second)
        # Then title deduplication removes third
        assert len(result) == 1
        assert result[0]["video_id"] == "vid1"
        assert result[0]["title"] == "First Video"

    def test_deduplicate_with_none_titles(self):
        """Test that videos with None titles are not deduplicated by title."""
        videos = [
            {"video_id": "vid1", "title": None},
            {"video_id": "vid2", "title": None},
            {"video_id": "vid3", "title": "Actual Title"},
            {"video_id": "vid4", "title": "Actual Title"},  # Should be deduplicated
        ]

        result = deduplicate_videos_by_id_and_title(videos)

        # None titles should not be deduplicated, but actual titles should
        assert len(result) == 3
        assert result[0]["video_id"] == "vid1"
        assert result[1]["video_id"] == "vid2"
        assert result[2]["video_id"] == "vid3"

    def test_deduplicate_with_empty_titles(self):
        """Test that videos with empty titles are not deduplicated by title."""
        videos = [
            {"video_id": "vid1", "title": ""},
            {"video_id": "vid2", "title": ""},
            {"video_id": "vid3", "title": "Valid Title"},
            {"video_id": "vid4", "title": "Valid Title"},  # Should be deduplicated
        ]

        result = deduplicate_videos_by_id_and_title(videos)

        # Empty titles should not be deduplicated, but valid titles should
        assert len(result) == 3
        assert result[0]["video_id"] == "vid1"
        assert result[1]["video_id"] == "vid2"
        assert result[2]["video_id"] == "vid3"

    def test_deduplicate_tiktok_caption_field(self):
        """Test deduplication with TikTok caption field."""
        videos = [
            {"id": "tiktok1", "caption": "Cool Product"},
            {"id": "tiktok2", "caption": "Cool Product"},  # Duplicate caption
            {"id": "tiktok3", "caption": "Another Product"},
        ]

        result = deduplicate_videos_by_id_and_title(
            videos,
            id_keys="id",
            title_key="caption"
        )

        # Should keep only first TikTok video with duplicate caption
        assert len(result) == 2
        assert result[0]["id"] == "tiktok1"
        assert result[1]["id"] == "tiktok3"
        assert result[0]["caption"] == "Cool Product"
        assert result[1]["caption"] == "Another Product"

    def test_deduplicate_multiple_id_keys(self):
        """Test deduplication with multiple ID keys."""
        videos = [
            {"video_id": "vid1", "title": "Video 1"},
            {"id": "id2", "title": "Video 2"},
            {"video_id": "vid3", "title": "Video 1"},  # Duplicate title
            {"content_id": "id4", "title": "Video 3"},
        ]

        result = deduplicate_videos_by_id_and_title(
            videos,
            id_keys=["video_id", "id", "content_id"]
        )

        # Should deduplicate by title after ID deduplication
        assert len(result) == 3
        assert result[0]["video_id"] == "vid1"
        assert result[1]["id"] == "id2"
        assert result[2]["content_id"] == "id4"

    def test_deduplicate_preserve_order(self):
        """Test that the original order is preserved as much as possible."""
        videos = [
            {"video_id": "vid1", "title": "Title A"},
            {"video_id": "vid2", "title": "Title B"},
            {"video_id": "vid3", "title": "Title A"},  # Duplicate title
            {"video_id": "vid4", "title": "Title C"},
            {"video_id": "vid5", "title": "Title B"},  # Duplicate title
        ]

        result = deduplicate_videos_by_id_and_title(videos)

        # Should preserve order of first occurrences
        assert len(result) == 3
        assert result[0]["video_id"] == "vid1"  # First Title A
        assert result[1]["video_id"] == "vid2"  # First Title B
        assert result[2]["video_id"] == "vid4"  # Title C

    def test_deduplicate_title_whitespace(self):
        """Test that title whitespace is handled correctly."""
        videos = [
            {"video_id": "vid1", "title": "Product Review"},
            {"video_id": "vid2", "title": "  Product Review  "},  # Same title with whitespace
            {"video_id": "vid3", "title": "Product Review "},
        ]

        result = deduplicate_videos_by_id_and_title(videos)

        # Should treat titles with different whitespace as duplicates
        assert len(result) == 1
        assert result[0]["video_id"] == "vid1"

    def test_deduplicate_no_ids(self):
        """Test deduplication when videos have no ID fields."""
        videos = [
            {"title": "Video 1"},
            {"title": "Video 1"},  # Duplicate title
            {"title": "Video 2"},
        ]

        result = deduplicate_videos_by_id_and_title(videos, id_keys=["nonexistent_id"])

        # Should still work with title deduplication
        assert len(result) == 2
        assert result[0]["title"] == "Video 1"
        assert result[1]["title"] == "Video 2"

    def test_deduplicate_empty_list(self):
        """Test deduplication with empty input list."""
        result = deduplicate_videos_by_id_and_title([])
        assert result == []

    def test_deduplicate_no_titles_field(self):
        """Test deduplication when videos have no title field."""
        videos = [
            {"video_id": "vid1"},
            {"video_id": "vid2"},
            {"video_id": "vid3"},
        ]

        result = deduplicate_videos_by_id_and_title(videos)

        # Should keep all videos since no titles to deduplicate by
        assert len(result) == 3
        assert result[0]["video_id"] == "vid1"
        assert result[1]["video_id"] == "vid2"
        assert result[2]["video_id"] == "vid3"

    def test_deduplicate_mixed_title_types(self):
        """Test deduplication with mixed title data types."""
        videos = [
            {"video_id": "vid1", "title": "Video Title"},
            {"video_id": "vid2", "title": "Video Title"},  # Duplicate string
            {"video_id": "vid3", "title": 123},  # Numeric title
            {"video_id": "vid4", "title": 123},  # Duplicate numeric
        ]

        result = deduplicate_videos_by_id_and_title(videos)

        # Should handle mixed types correctly
        assert len(result) == 2
        assert result[0]["video_id"] == "vid1"
        assert result[1]["video_id"] == "vid3"

    def test_case_sensitive_titles(self):
        """Test that title deduplication is case-sensitive."""
        videos = [
            {"video_id": "vid1", "title": "Product Review"},
            {"video_id": "vid2", "title": "product review"},  # Different case
            {"video_id": "vid3", "title": "Product Review"},  # Exact match
        ]

        result = deduplicate_videos_by_id_and_title(videos)

        # Should treat different cases as different titles
        assert len(result) == 2
        assert result[0]["video_id"] == "vid1"
        assert result[1]["video_id"] == "vid2"
