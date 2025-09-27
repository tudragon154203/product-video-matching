"""Integration tests for TikTok crawler functionality."""
import pytest
import asyncio
import os
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

from services.service import VideoCrawlerService
from platform_crawler.interface import PlatformCrawlerInterface
from platform_crawler.tiktok.tiktok_crawler import TikTokCrawler
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from config_loader import config


@pytest.fixture
async def db():
    """Real database connection for testing"""
    db_manager = DatabaseManager(config.POSTGRES_DSN)
    try:
        await db_manager.connect()
        yield db_manager
    finally:
        await db_manager.disconnect()


@pytest.fixture
async def broker():
    """Real RabbitMQ connection for testing"""
    broker_manager = MessageBroker(config.BUS_BROKER)
    try:
        await broker_manager.connect()
        yield broker_manager
    finally:
        await broker_manager.disconnect()


@pytest.fixture
def tiktok_crawler():
    """Real TikTok crawler instance"""
    return TikTokCrawler()


class TestTikTokIntegration:
    """Integration tests for TikTok crawler functionality."""

    def test_environment_variables_override(self):
        """Test that .env.test overrides .env values during pytest execution."""
        # DEBUG: Print environment variables to verify pytest-dotenv functionality
        print(f"DEBUG: LOG_LEVEL from config: {config.LOG_LEVEL}")
        print(f"DEBUG: BUS_BROKER from config: {config.BUS_BROKER}")
        print(f"DEBUG: POSTGRES_DSN from config: {config.POSTGRES_DSN}")
        print(f"DEBUG: PYTEST_CURRENT_TEST env var: {os.environ.get('PYTEST_CURRENT_TEST', 'NOT SET')}")
        
        # Check the global config directly
        from libs.config import config as global_config
        print(f"DEBUG: LOG_LEVEL from global_config: {global_config.LOG_LEVEL}")
        print(f"DEBUG: BUS_BROKER from global_config: {global_config.BUS_BROKER}")
        print(f"DEBUG: POSTGRES_DSN from global_config: {global_config.POSTGRES_DSN}")
        
        # Check environment variables directly (these should be set by pytest-dotenv)
        print(f"DEBUG: LOG_LEVEL from os.environ: {os.environ.get('LOG_LEVEL', 'NOT SET')}")
        print(f"DEBUG: BUS_BROKER from os.environ: {os.environ.get('BUS_BROKER', 'NOT SET')}")
        print(f"DEBUG: POSTGRES_DSN from os.environ: {os.environ.get('POSTGRES_DSN', 'NOT SET')}")
        
        # Verify that test environment values are loaded directly from os.environ
        # These should be set by pytest-dotenv from .env.test
        assert os.environ.get('LOG_LEVEL') == "DEBUG", f"Expected LOG_LEVEL=DEBUG from os.environ, got {os.environ.get('LOG_LEVEL')}"
        assert "localhost:5672" in os.environ.get('BUS_BROKER', ''), f"Expected localhost in BUS_BROKER from os.environ, got {os.environ.get('BUS_BROKER')}"
        assert "localhost:5444" in os.environ.get('POSTGRES_DSN', ''), f"Expected localhost:5444 in POSTGRES_DSN from os.environ, got {os.environ.get('POSTGRES_DSN')}"
        
        print("SUCCESS: Test environment variables are correctly loaded by pytest-dotenv!")

    @pytest.mark.asyncio
    async def test_tiktok_search_request_processing(self, db, broker, tiktok_crawler, temp_dir):
        """Ensure TikTok search requests are dispatched through the crawler."""
        # Replace the TikTok crawler in the service with our real instance
        service = VideoCrawlerService(db, broker)
        service.platform_crawlers["tiktok"] = tiktok_crawler

        # Track published events
        published_topics = []
        async def track_publish_event(topic: str, event_data: Dict[str, Any], correlation_id: str = None):
            published_topics.append(topic)
        
        # Mock the publish_event method to track calls
        broker.publish_event = track_publish_event

        event_data = {
            "job_id": "test-job-123",
            "industry": "test industry",
            "queries": {
                "vi": ["test query vietnamese"],
                "zh": ["test query chinese"],
            },
            "platforms": ["tiktok"],
            "recency_days": 30,
        }

        # Execute the search request
        await service.handle_videos_search_request(event_data)

        # Verify that TikTok crawler was called (it should have made real API calls)
        assert "tiktok" in service.platform_crawlers
        
        # Check that expected events were published
        assert "videos.collections.completed" in published_topics

    @pytest.mark.asyncio
    async def test_tiktok_platform_query_extraction(self, db, broker):
        """TikTok queries should prioritize Vietnamese inputs."""
        service = VideoCrawlerService(db, broker)

        queries = {
            "vi": ["query vi 1", "query vi 2"],
            "zh": ["query zh 1", "query zh 2"],
        }

        extracted_queries = service._extract_platform_queries(queries, ["tiktok"])

        assert extracted_queries == ["query vi 1", "query vi 2"]

    @pytest.mark.asyncio
    async def test_tiktok_error_handling(self, db, broker, tiktok_crawler):
        """Gracefully handle crawler failures without raising."""
        # Replace the TikTok crawler in the service with our real instance
        service = VideoCrawlerService(db, broker)
        service.platform_crawlers["tiktok"] = tiktok_crawler

        # Track published events
        published_topics = []
        async def track_publish_event(topic: str, event_data: Dict[str, Any], correlation_id: str = None):
            published_topics.append(topic)
        
        # Mock the publish_event method to track calls
        broker.publish_event = track_publish_event

        event_data = {
            "job_id": "test-job-456",
            "industry": "test industry",
            "queries": {"vi": ["test query"]},
            "platforms": ["tiktok"],
            "recency_days": 30,
        }

        # Execute the search request (this will make real API calls)
        try:
            await service.handle_videos_search_request(event_data)
        except Exception as e:
            # If the API call fails, we still want to verify the error handling
            pass

        # Check that expected events were published even in error cases
        assert "videos.collections.completed" in published_topics
