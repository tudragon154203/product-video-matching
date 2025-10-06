"""Unit tests for PlatformQueryProcessor."""

from services.platform_query_processor import PlatformQueryProcessor
import pytest

pytestmark = pytest.mark.unit


class TestPlatformQueryProcessor:
    """Tests for PlatformQueryProcessor class."""

    def test_extract_platform_queries_tiktok_vietnamese(self):
        """Test that TikTok platform extracts Vietnamese queries."""
        queries = {
            "vi": ["gối ergonomic", "pillow thoải mái"],
            "zh": ["人体工学枕头", "舒适枕头"]
        }
        platforms = ["tiktok"]

        extracted = PlatformQueryProcessor.extract_platform_queries(queries, platforms)

        assert isinstance(extracted, list)
        assert extracted == ["gối ergonomic", "pillow thoải mái"]

    def test_extract_platform_queries_youtube_tiktok_vietnamese(self):
        """Test that YouTube+TikTok platforms extract Vietnamese queries."""
        queries = {
            "vi": ["gối ergonomic", "pillow thoải mái"],
            "zh": ["人体工学枕头", "舒适枕头"]
        }
        platforms = ["youtube", "tiktok"]

        extracted = PlatformQueryProcessor.extract_platform_queries(queries, platforms)

        assert isinstance(extracted, list)
        assert extracted == ["gối ergonomic", "pillow thoải mái"]

    def test_extract_platform_queries_other_platforms_aggregate(self):
        """Test that other platforms aggregate all queries."""
        queries = {
            "en": ["ergonomic pillow", "comfort pillow"],
            "zh": ["人体工学枕头", "舒适枕头"]
        }
        platforms = ["bilibili", "douyin"]

        extracted = PlatformQueryProcessor.extract_platform_queries(queries, platforms)

        assert isinstance(extracted, list)
        assert len(extracted) == 4
        assert "ergonomic pillow" in extracted
        assert "comfort pillow" in extracted
        assert "人体工学枕头" in extracted
        assert "舒适枕头" in extracted

    def test_extract_platform_queries_mixed_platforms_vietnamese_priority(self):
        """Test that Vietnamese queries are prioritized when TikTok/YouTube are included."""
        queries = {
            "vi": ["gối ergonomic"],
            "en": ["ergonomic pillow"],
            "zh": ["人体工学枕头"]
        }
        platforms = ["youtube", "bilibili"]

        extracted = PlatformQueryProcessor.extract_platform_queries(queries, platforms)

        assert isinstance(extracted, list)
        assert extracted == ["gối ergonomic"]

    def test_extract_platform_queries_string_input(self):
        """Test processing of string query input."""
        queries = "single query"
        platforms = ["youtube"]

        extracted = PlatformQueryProcessor.extract_platform_queries(queries, platforms)

        assert isinstance(extracted, list)
        assert extracted == ["single query"]

    def test_extract_platform_queries_list_input(self):
        """Test processing of list query input."""
        queries = ["query1", "query2", "query3"]
        platforms = ["youtube"]

        extracted = PlatformQueryProcessor.extract_platform_queries(queries, platforms)

        assert isinstance(extracted, list)
        assert extracted == ["query1", "query2", "query3"]

    def test_extract_platform_queries_empty_platforms(self):
        """Test behavior with empty platforms list."""
        queries = {"vi": ["query1"]}
        platforms = []

        extracted = PlatformQueryProcessor.extract_platform_queries(queries, platforms)

        assert extracted == []

    def test_extract_platform_queries_none_queries(self):
        """Test behavior with None queries."""
        queries = None
        platforms = ["youtube"]

        extracted = PlatformQueryProcessor.extract_platform_queries(queries, platforms)

        assert extracted == []

    def test_extract_platform_queries_empty_dict(self):
        """Test behavior with empty query dict."""
        queries = {}
        platforms = ["youtube"]

        extracted = PlatformQueryProcessor.extract_platform_queries(queries, platforms)

        assert extracted == []

    def test_normalize_to_list_string(self):
        """Test _normalize_to_list with string input."""
        result = PlatformQueryProcessor._normalize_to_list("test string")
        assert result == ["test string"]

    def test_normalize_to_list_list(self):
        """Test _normalize_to_list with list input."""
        result = PlatformQueryProcessor._normalize_to_list(["item1", "item2"])
        assert result == ["item1", "item2"]

    def test_normalize_to_list_tuple(self):
        """Test _normalize_to_list with tuple input."""
        result = PlatformQueryProcessor._normalize_to_list(("item1", "item2"))
        assert result == ["item1", "item2"]

    def test_normalize_to_list_set(self):
        """Test _normalize_to_list with set input."""
        result = PlatformQueryProcessor._normalize_to_list({"item1", "item2"})
        assert len(result) == 2
        assert "item1" in result
        assert "item2" in result

    def test_normalize_to_list_none(self):
        """Test _normalize_to_list with None input."""
        result = PlatformQueryProcessor._normalize_to_list(None)
        assert result == []

    def test_normalize_to_list_mixed_types(self):
        """Test _normalize_to_list with mixed types in list."""
        result = PlatformQueryProcessor._normalize_to_list(["item1", "", "item2", None])
        assert result == ["item1", "item2"]

    def test_dedupe_preserve_order(self):
        """Test _dedupe_preserve_order removes duplicates while preserving order."""
        items = ["item1", "item2", "item1", "item3", "item2", "item4"]
        result = PlatformQueryProcessor._dedupe_preserve_order(items)

        assert result == ["item1", "item2", "item3", "item4"]

    def test_dedupe_preserve_order_empty(self):
        """Test _dedupe_preserve_order with empty list."""
        result = PlatformQueryProcessor._dedupe_preserve_order([])
        assert result == []

    def test_dedupe_preserve_order_with_empty_strings(self):
        """Test _dedupe_preserve_order filters empty strings."""
        items = ["item1", "", "item2", "", "item3"]
        result = PlatformQueryProcessor._dedupe_preserve_order(items)

        assert result == ["item1", "item2", "item3"]