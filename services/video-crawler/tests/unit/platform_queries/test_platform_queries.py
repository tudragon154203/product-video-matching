"""Unit tests for platform-specific query extraction logic."""

from services.platform_query_processor import PlatformQueryProcessor
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))


pytestmark = pytest.mark.unit


class TestPlatformQueryExtraction:
    """Tests for platform-specific query extraction functionality."""

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

    def test_extract_platform_queries_multiple_platforms(self):
        """Test query extraction with multiple platforms including TikTok."""
        queries = {
            "vi": ["query vi 1", "query vi 2"],
            "zh": ["query zh 1", "query zh 2"]
        }
        platforms = ["youtube", "tiktok", "bilibili"]

        extracted = PlatformQueryProcessor.extract_platform_queries(queries, platforms)

        assert isinstance(extracted, list)
        assert extracted == ["query vi 1", "query vi 2"]

    def test_extract_platform_queries_tiktok_only(self):
        """Test query extraction for TikTok platform only."""
        queries = {
            "vi": ["đánh giá tai nghe không dây", "unbox iphone 15"],
            "en": ["wireless earbuds review 2024"]
        }
        platforms = ["tiktok"]

        extracted = PlatformQueryProcessor.extract_platform_queries(queries, platforms)

        assert isinstance(extracted, list)
        assert len(extracted) == 2
        assert "đánh giá tai nghe không dây" in extracted
        assert "unbox iphone 15" in extracted
        assert "wireless earbuds review 2024" not in extracted

    def test_extract_platform_queries_youtube_without_vietnamese(self):
        """When Vietnamese queries are absent, YouTube should not fall back to other languages."""
        queries = {
            "zh": ["产品评测"],
            "en": ["product review"]
        }
        platforms = ["youtube"]

        extracted = PlatformQueryProcessor.extract_platform_queries(queries, platforms)

        assert extracted == []

    def test_extract_platform_queries_invalid_input(self):
        """Test query extraction with invalid input formats."""
        extracted = PlatformQueryProcessor.extract_platform_queries(["query1", "query2"], ["tiktok"])
        assert isinstance(extracted, list)

        extracted = PlatformQueryProcessor.extract_platform_queries({"vi": ["query1"]}, [])
        assert extracted == []

        extracted = PlatformQueryProcessor.extract_platform_queries(None, ["tiktok"])
        assert extracted == []

    def test_extract_platform_queries_edge_cases(self):
        """Test edge cases for query extraction."""
        extracted = PlatformQueryProcessor.extract_platform_queries({"vi": [], "zh": []}, ["tiktok"])
        assert extracted == []

        extracted = PlatformQueryProcessor.extract_platform_queries({}, ["tiktok"])
        assert extracted == []

        extracted = PlatformQueryProcessor.extract_platform_queries({"vi": "single query"}, ["tiktok"])
        assert extracted == ["single query"]
