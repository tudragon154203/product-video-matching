"""Unit tests for platform-specific query extraction logic."""

from pathlib import Path
import sys
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from services.service import VideoCrawlerService


pytestmark = pytest.mark.unit


@pytest.fixture
def query_service(tiktok_env_mock):
    """Create a VideoCrawlerService instance without touching global crawler state."""
    with patch.object(VideoCrawlerService, "_initialize_platform_crawlers", return_value={}):
        service = VideoCrawlerService(None, None, tiktok_env_mock)
    service.initialize_keyframe_extractor(keyframe_dir=tiktok_env_mock)
    return service


class TestPlatformQueryExtraction:
    """Tests for platform-specific query extraction functionality."""

    def test_extract_platform_queries_tiktok_vietnamese(self, query_service):
        """Test that TikTok platform extracts Vietnamese queries."""
        queries = {
            "vi": ["gối ergonomic", "pillow thoải mái"],
            "zh": ["人体工学枕头", "舒适枕头"]
        }
        platforms = ["tiktok"]

        extracted = query_service._extract_platform_queries(queries, platforms)

        assert isinstance(extracted, list)
        assert len(extracted) > 0

    def test_extract_platform_queries_multiple_platforms(self, query_service):
        """Test query extraction with multiple platforms including TikTok."""
        queries = {
            "vi": ["query vi 1", "query vi 2"],
            "zh": ["query zh 1", "query zh 2"]
        }
        platforms = ["youtube", "tiktok", "bilibili"]

        extracted = query_service._extract_platform_queries(queries, platforms)

        assert isinstance(extracted, list)
        assert len(extracted) == 4

    def test_extract_platform_queries_tiktok_only(self, query_service):
        """Test query extraction for TikTok platform only."""
        queries = {
            "vi": ["đánh giá tai nghe không dây", "unbox iphone 15"],
            "en": ["wireless earbuds review 2024"]
        }
        platforms = ["tiktok"]

        extracted = query_service._extract_platform_queries(queries, platforms)

        assert isinstance(extracted, list)
        assert len(extracted) == 2
        assert "đánh giá tai nghe không dây" in extracted
        assert "unbox iphone 15" in extracted
        assert "wireless earbuds review 2024" not in extracted

    def test_extract_platform_queries_invalid_input(self, query_service):
        """Test query extraction with invalid input formats."""
        extracted = query_service._extract_platform_queries(["query1", "query2"], ["tiktok"])
        assert isinstance(extracted, list)

        extracted = query_service._extract_platform_queries({"vi": ["query1"]}, [])
        assert extracted == []

        extracted = query_service._extract_platform_queries(None, ["tiktok"])
        assert extracted == []

    def test_extract_platform_queries_edge_cases(self, query_service):
        """Test edge cases for query extraction."""
        extracted = query_service._extract_platform_queries({"vi": [], "zh": []}, ["tiktok"])
        assert extracted == []

        extracted = query_service._extract_platform_queries({}, ["tiktok"])
        assert extracted == []

        extracted = query_service._extract_platform_queries({"vi": "single query"}, ["tiktok"])
        assert extracted == ["single query"]
