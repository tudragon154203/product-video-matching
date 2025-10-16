"""
Event publishing utilities for collection phase integration tests.
Provides helpers for publishing test events and validating event flow.
"""
import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from common_py.messaging import MessageBroker
from common_py.logging_config import configure_logging

logger = configure_logging("test-utils:event-publisher")


class CollectionEventPublisher:
    """
    Event publisher for collection phase integration tests.
    Provides methods to publish standard collection events with test data.
    """

    def __init__(self, message_broker: MessageBroker):
        self.broker = message_broker
        self.published_events = []
        # Idempotency guard: track correlation_ids we've already published per topic
        self._idempotent_correlation_ids = {
            "products.collect.request": set(),
            "videos.search.request": set(),
        }

    async def publish_products_collect_request(
        self,
        job_id: str,
        queries: Dict[str, List[str]],
        top_amz: int = 20,
        top_ebay: int = 20,
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Publish a products collect request event.

        Args:
            job_id: Unique job identifier
            queries: Search queries by language (e.g., {"en": ["query1", "query2"]})
            top_amz: Number of top Amazon products to collect
            top_ebay: Number of top eBay products to collect
            correlation_id: Optional correlation ID for tracing

        Returns:
            The correlation ID used
        """
        event_data = {
            "job_id": job_id,
            "top_amz": top_amz,
            "top_ebay": top_ebay,
            "queries": queries
        }

        correlation_id = correlation_id or str(uuid.uuid4())

        # Idempotency: skip re-publish if this correlation_id has already been used for this topic
        if correlation_id in self._idempotent_correlation_ids["products.collect.request"]:
            logger.info(
                "Skipping duplicate products.collect.request due to idempotent correlation_id",
                job_id=job_id,
                correlation_id=correlation_id
            )
            return correlation_id

        await self.broker.publish_event(
            topic="products.collect.request",
            event_data=event_data,
            correlation_id=correlation_id
        )
        # Record correlation_id for idempotency tracking
        self._idempotent_correlation_ids["products.collect.request"].add(correlation_id)

        # Track published event
        self.published_events.append({
            "topic": "products.collect.request",
            "event_data": event_data,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        logger.info(
            "Published products collect request",
            job_id=job_id,
            correlation_id=correlation_id,
            queries_count=len(queries.get("en", []))
        )

        return correlation_id

    async def publish_videos_search_request(
        self,
        job_id: str,
        industry: str,
        queries: Dict[str, List[str]],
        platforms: List[str],
        recency_days: int = 30,
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Publish a videos search request event.

        Args:
            job_id: Unique job identifier
            industry: Industry keyword for video search
            queries: Search queries by language (e.g., {"vi": ["query1"], "zh": ["query2"]})
            platforms: List of video platforms (e.g., ["youtube", "tiktok"])
            recency_days: How many days back to search for videos
            correlation_id: Optional correlation ID for tracing

        Returns:
            The correlation ID used
        """
        event_data = {
            "job_id": job_id,
            "industry": industry,
            "queries": queries,
            "platforms": platforms,
            "recency_days": recency_days
        }

        correlation_id = correlation_id or str(uuid.uuid4())

        # Idempotency: skip re-publish if this correlation_id has already been used for this topic
        if correlation_id in self._idempotent_correlation_ids["videos.search.request"]:
            logger.info(
                "Skipping duplicate videos.search.request due to idempotent correlation_id",
                job_id=job_id,
                correlation_id=correlation_id
            )
            return correlation_id

        await self.broker.publish_event(
            topic="videos.search.request",
            event_data=event_data,
            correlation_id=correlation_id
        )
        # Record correlation_id for idempotency tracking
        self._idempotent_correlation_ids["videos.search.request"].add(correlation_id)

        # Track published event
        self.published_events.append({
            "topic": "videos.search.request",
            "event_data": event_data,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        logger.info(
            "Published videos search request",
            job_id=job_id,
            correlation_id=correlation_id,
            industry=industry,
            platforms=platforms
        )

        return correlation_id

    async def publish_mock_products_collections_completed(
        self,
        job_id: str,
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Publish a mock products collections completed event for testing.

        Args:
            job_id: Unique job identifier
            correlation_id: Optional correlation ID for tracing

        Returns:
            The correlation ID used
        """
        event_data = {
            "job_id": job_id,
            "event_id": str(uuid.uuid4())
        }

        correlation_id = correlation_id or str(uuid.uuid4())

        await self.broker.publish_event(
            topic="products.collections.completed",
            event_data=event_data,
            correlation_id=correlation_id
        )

        # Track published event
        self.published_events.append({
            "topic": "products.collections.completed",
            "event_data": event_data,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        logger.info(
            "Published mock products collections completed",
            job_id=job_id,
            correlation_id=correlation_id
        )

        return correlation_id

    async def publish_mock_videos_collections_completed(
        self,
        job_id: str,
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Publish a mock videos collections completed event for testing.

        Args:
            job_id: Unique job identifier
            correlation_id: Optional correlation ID for tracing

        Returns:
            The correlation ID used
        """
        event_data = {
            "job_id": job_id,
            "event_id": str(uuid.uuid4())
        }

        correlation_id = correlation_id or str(uuid.uuid4())

        await self.broker.publish_event(
            topic="videos.collections.completed",
            event_data=event_data,
            correlation_id=correlation_id
        )

        # Track published event
        self.published_events.append({
            "topic": "videos.collections.completed",
            "event_data": event_data,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        logger.info(
            "Published mock videos collections completed",
            job_id=job_id,
            correlation_id=correlation_id
        )

        return correlation_id

    async def publish_collection_phase_complete(
        self,
        job_id: str,
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Publish both products and videos collections completed events.

        Args:
            job_id: Unique job identifier
            correlation_id: Optional correlation ID for tracing

        Returns:
            The correlation ID used
        """
        correlation_id = correlation_id or str(uuid.uuid4())

        # Publish both events
        await self.publish_mock_products_collections_completed(job_id, correlation_id)
        await self.publish_mock_videos_collections_completed(job_id, correlation_id)

        logger.info(
            "Published collection phase complete events",
            job_id=job_id,
            correlation_id=correlation_id
        )

        return correlation_id

    def get_published_events(self, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all published events, optionally filtered by topic.

        Args:
            topic: Optional topic to filter by

        Returns:
            List of published events
        """
        if topic:
            return [event for event in self.published_events if event["topic"] == topic]
        return self.published_events.copy()

    def get_published_events_by_correlation_id(self, correlation_id: str) -> List[Dict[str, Any]]:
        """
        Get published events filtered by correlation ID.

        Args:
            correlation_id: Correlation ID to filter by

        Returns:
            List of published events with the given correlation ID
        """
        return [
            event for event in self.published_events
            if event["correlation_id"] == correlation_id
        ]

    def clear_published_events(self):
        """Clear the tracking of published events"""
        self.published_events.clear()
        logger.info("Cleared published events tracking")


class EventValidator:
    """
    Utilities for validating events during integration tests.
    """

    @staticmethod
    def validate_products_collect_request(event_data: Dict[str, Any]) -> bool:
        """Validate a products collect request event"""
        required_fields = ["job_id", "top_amz", "top_ebay", "queries"]

        for field in required_fields:
            if field not in event_data:
                return False

        # Validate queries structure
        queries = event_data["queries"]
        if not isinstance(queries, dict) or "en" not in queries:
            return False

        if not isinstance(queries["en"], list) or len(queries["en"]) == 0:
            return False

        return True

    @staticmethod
    def validate_videos_search_request(event_data: Dict[str, Any]) -> bool:
        """Validate a videos search request event"""
        required_fields = ["job_id", "industry", "queries", "platforms", "recency_days"]

        for field in required_fields:
            if field not in event_data:
                return False

        # Validate queries structure
        queries = event_data["queries"]
        if not isinstance(queries, dict):
            return False

        # Validate platforms
        platforms = event_data["platforms"]
        if not isinstance(platforms, list) or len(platforms) == 0:
            return False

        valid_platforms = ["youtube", "bilibili", "douyin", "tiktok"]
        for platform in platforms:
            if platform not in valid_platforms:
                return False

        return True

    @staticmethod
    def validate_collections_completed(event_data: Dict[str, Any]) -> bool:
        """Validate a collections completed event"""
        required_fields = ["job_id", "event_id"]

        for field in required_fields:
            if field not in event_data:
                return False

        # Validate UUID format for event_id
        try:
            uuid.UUID(event_data["event_id"])
        except ValueError:
            return False

        return True

    @staticmethod
    def extract_job_id_from_event(event: Dict[str, Any]) -> Optional[str]:
        """Extract job ID from an event message"""
        if "event_data" in event:
            return event["event_data"].get("job_id")
        return event.get("job_id")

    @staticmethod
    def extract_correlation_id_from_event(event: Dict[str, Any]) -> Optional[str]:
        """Extract correlation ID from an event message"""
        return event.get("correlation_id")

    @staticmethod
    def extract_event_id_from_event(event: Dict[str, Any]) -> Optional[str]:
        """Extract event ID from an event message"""
        if "event_data" in event:
            return event["event_data"].get("event_id")
        return event.get("event_id")


class TestEventFactory:
    """
    Factory for creating test events with realistic data.
    """

    @staticmethod
    def create_products_collect_request(
        job_id: str = "test_job_123",
        queries: Optional[List[str]] = None,
        top_amz: int = 20,
        top_ebay: int = 20
    ) -> Dict[str, Any]:
        """Create a test products collect request event"""
        if queries is None:
            queries = ["ergonomic pillows", "memory foam cushions"]

        return {
            "job_id": job_id,
            "top_amz": top_amz,
            "top_ebay": top_ebay,
            "queries": {
                "en": queries
            }
        }

    @staticmethod
    def create_videos_search_request(
        job_id: str = "test_job_123",
        industry: str = "test pillows",
        queries: Optional[Dict[str, List[str]]] = None,
        platforms: Optional[List[str]] = None,
        recency_days: int = 30
    ) -> Dict[str, Any]:
        """Create a test videos search request event"""
        if queries is None:
            queries = {
                "vi": ["gối ngủ ergonomics", "đánh giá gối memory foam"],
                "zh": ["人体工学枕头", "记忆泡沫枕头测评"]
            }

        if platforms is None:
            platforms = ["youtube", "tiktok"]

        return {
            "job_id": job_id,
            "industry": industry,
            "queries": queries,
            "platforms": platforms,
            "recency_days": recency_days
        }

    @staticmethod
    def create_collections_completed(
        job_id: str = "test_job_123",
        event_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a test collections completed event"""
        if event_id is None:
            event_id = str(uuid.uuid4())

        return {
            "job_id": job_id,
            "event_id": event_id
        }

    @staticmethod
    def create_test_job_id() -> str:
        """Create a test job ID with timestamp"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"test_job_{timestamp}_{uuid.uuid4().hex[:8]}"
