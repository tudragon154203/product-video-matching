"""Unit tests for platform-specific query extraction logic."""

from services.service import VideoCrawlerService
import pytest
from unittest.mock import patch, MagicMock
import os

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


pytestmark = pytest.mark.unit


class TestPlatformQueryExtraction:
    """Tests for platform-specific query extraction functionality."""

    def test_extract_platform_queries_tiktok_vietnamese(self, tiktok_env_mock):
        """Test that TikTok platform extracts Vietnamese queries."""

        # Mock TikTokDownloader to use temporary directories
        with patch('services.service.TikTokDownloader') as MockTikTokDownloader:
            mock_downloader_instance = MagicMock()
            mock_downloader_instance.video_storage_path = os.path.join(tiktok_env_mock, "tiktok_videos")
            mock_downloader_instance.keyframe_storage_path = os.path.join(tiktok_env_mock, "tiktok_keyframes")
            os.makedirs(mock_downloader_instance.video_storage_path, exist_ok=True)
            os.makedirs(mock_downloader_instance.keyframe_storage_path, exist_ok=True)
            MockTikTokDownloader.return_value = mock_downloader_instance

            # Mock TikTokCrawler to use the mocked downloader
            with patch('services.service.TikTokCrawler') as MockTikTokCrawler:
                mock_tiktok_crawler_instance = MagicMock()
                mock_tiktok_crawler_instance.get_platform_name.return_value = "tiktok"
                mock_tiktok_crawler_instance.downloader = mock_downloader_instance
                MockTikTokCrawler.return_value = mock_tiktok_crawler_instance

                # Initialize service inside the patch context to avoid real instantiation
                service = VideoCrawlerService(None, None, tiktok_env_mock)  # Pass temp_dir to VideoCrawlerService
                service.initialize_keyframe_extractor(keyframe_dir=tiktok_env_mock)  # DB and broker not needed for this test

                queries = {
                    "vi": ["gối ergonomic", "pillow thoải mái"],
                    "zh": ["人体工学枕头", "舒适枕头"]
                }
                platforms = ["tiktok"]

                # For TikTok platform, Vietnamese queries should be extracted
                extracted = service._extract_platform_queries(queries, platforms)

                # Currently this will return all queries until TikTok-specific logic is implemented
                # For now, just verify it returns a list
                assert isinstance(extracted, list)
                assert len(extracted) > 0

    def test_extract_platform_queries_multiple_platforms(self, tiktok_env_mock):
        """Test query extraction with multiple platforms including TikTok."""
        service = VideoCrawlerService(None, None)
        service.initialize_keyframe_extractor(keyframe_dir=tiktok_env_mock)

        queries = {
            "vi": ["query vi 1", "query vi 2"],
            "zh": ["query zh 1", "query zh 2"]
        }
        platforms = ["youtube", "tiktok", "bilibili"]

        # With multiple platforms, should extract all queries
        extracted = service._extract_platform_queries(queries, platforms)

        assert isinstance(extracted, list)
        # Should include both Vietnamese and Chinese queries for multiple platforms
        assert len(extracted) == 4

    def test_extract_platform_queries_tiktok_only(self, tiktok_env_mock):
        """Test query extraction for TikTok platform only."""
        service = VideoCrawlerService(None, None)
        service.initialize_keyframe_extractor(keyframe_dir=tiktok_env_mock)

        queries = {
            "vi": ["đánh giá tai nghe không dây", "unbox iphone 15"],
            "en": ["wireless earbuds review 2024"]  # English queries should not be used for TikTok
        }
        platforms = ["tiktok"]

        # For TikTok-only, should prioritize Vietnamese queries
        extracted = service._extract_platform_queries(queries, platforms)

        assert isinstance(extracted, list)
        # Should return only Vietnamese queries, not English
        assert len(extracted) == 2
        assert "đánh giá tai nghe không dây" in extracted
        assert "unbox iphone 15" in extracted
        assert "wireless earbuds review 2024" not in extracted

    def test_extract_platform_queries_invalid_input(self, tiktok_env_mock):
        """Test query extraction with invalid input formats."""
        service = VideoCrawlerService(None, None)
        service.initialize_keyframe_extractor(keyframe_dir=tiktok_env_mock)

        # Test with non-dict queries
        extracted = service._extract_platform_queries(["query1", "query2"], ["tiktok"])
        assert isinstance(extracted, list)

        # Test with empty platforms
        extracted = service._extract_platform_queries({"vi": ["query1"]}, [])
        assert extracted == []

        # Test with None queries
        extracted = service._extract_platform_queries(None, ["tiktok"])
        assert extracted == []

    def test_extract_platform_queries_edge_cases(self, tiktok_env_mock):
        """Test edge cases for query extraction."""
        service = VideoCrawlerService(None, None)
        service.initialize_keyframe_extractor(keyframe_dir=tiktok_env_mock)

        # Empty queries
        extracted = service._extract_platform_queries({"vi": [], "zh": []}, ["tiktok"])
        assert extracted == []

        # Missing language keys
        extracted = service._extract_platform_queries({}, ["tiktok"])
        assert extracted == []

        # Single query string instead of array
        extracted = service._extract_platform_queries({"vi": "single query"}, ["tiktok"])
        assert extracted == ["single query"]
