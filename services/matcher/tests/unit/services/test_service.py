"""Unit tests for the matcher service facade."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker

from services.service import MatcherService

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_db() -> MagicMock:
    """Create a mock database manager."""

    db = MagicMock(spec=DatabaseManager)
    db.fetch_all = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_broker() -> MagicMock:
    """Create a mock message broker."""

    broker = MagicMock(spec=MessageBroker)
    broker.subscribe_to_topic = AsyncMock()
    broker.publish_event = AsyncMock()
    return broker


@pytest.fixture
def matcher_service(
    mock_db: MagicMock,
    mock_broker: MagicMock,
) -> MatcherService:
    """Provide a matcher service wired to mock dependencies."""

    return MatcherService(
        mock_db,
        mock_broker,
        "/data",
        retrieval_topk=10,
        sim_deep_min=0.82,
        inliers_min=0.35,
        match_best_min=0.88,
        match_cons_min=2,
        match_accept=0.80,
    )


class TestMatcherService:
    """Behavioural tests for the matcher service."""

    @pytest.mark.asyncio
    async def test_initialize(self, matcher_service: MatcherService) -> None:
        with patch.object(
            matcher_service.matching_engine,
            "initialize",
        ) as mock_init:
            await matcher_service.initialize()
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup(self, matcher_service: MatcherService) -> None:
        with patch.object(
            matcher_service.matching_engine,
            "cleanup",
        ) as mock_cleanup:
            await matcher_service.cleanup()
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_products(
        self,
        matcher_service: MatcherService,
        mock_db: MagicMock,
    ) -> None:
        mock_db.fetch_all.return_value = [
            {"product_id": "product_001", "title": "Product 1"},
            {"product_id": "product_002", "title": "Product 2"},
        ]

        products = await matcher_service.get_job_products("job_001")

        mock_db.fetch_all.assert_called_once()
        args, _ = mock_db.fetch_all.call_args
        query = args[0]
        assert "products" in query
        assert "WHERE p.job_id = $1" in query
        assert args[1] == "job_001"
        assert len(products) == 2

    @pytest.mark.asyncio
    async def test_get_job_videos(
        self,
        matcher_service: MatcherService,
        mock_db: MagicMock,
    ) -> None:
        mock_db.fetch_all.return_value = [
            {"video_id": "video_001", "title": "Video 1"},
            {"video_id": "video_002", "title": "Video 2"},
        ]

        videos = await matcher_service.get_job_videos("job_001")

        mock_db.fetch_all.assert_called_once()
        args, _ = mock_db.fetch_all.call_args
        query = args[0]
        assert "videos" in query
        assert "WHERE v.job_id = $1" in query
        assert args[1] == "job_001"
        assert len(videos) == 2

    @pytest.mark.asyncio
    async def test_handle_match_request_success(
        self,
        matcher_service: MatcherService,
        mock_db: MagicMock,
        mock_broker: MagicMock,
    ) -> None:
        mock_db.fetch_all.side_effect = [
            [{"product_id": "product_001", "title": "Product 1"}],
            [{"video_id": "video_001", "title": "Video 1"}],
        ]

        with patch.object(
            matcher_service.matching_engine,
            "match_product_video",
            return_value={
                "best_img_id": "img_001",
                "best_frame_id": "frame_001",
                "ts": 1.0,
                "score": 0.85,
                "best_pair_score": 0.88,
                "consistency": 3,
                "total_pairs": 5,
            },
        ) as mock_match:
            with patch.object(
                matcher_service,
                "match_crud",
            ) as mock_crud:
                mock_crud.create_match = AsyncMock()

                event_data = {
                    "job_id": "job_001",
                    "event_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                }

                await matcher_service.handle_match_request(event_data)

                mock_match.assert_called_once_with(
                    "product_001",
                    "video_001",
                    "job_001",
                )
                mock_crud.create_match.assert_called_once()
                mock_broker.publish_event.assert_called()
                call_args = mock_broker.publish_event.call_args
                assert call_args[0][0] == "matchings.process.completed"

    @pytest.mark.asyncio
    async def test_handle_match_request_no_match(
        self,
        matcher_service: MatcherService,
        mock_db: MagicMock,
    ) -> None:
        mock_db.fetch_all.side_effect = [
            [{"product_id": "product_001", "title": "Product 1"}],
            [{"video_id": "video_001", "title": "Video 1"}],
        ]

        with patch.object(
            matcher_service.matching_engine,
            "match_product_video",
            return_value=None,
        ) as mock_match:
            event_data = {
                "job_id": "job_001",
                "event_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
            }

            await matcher_service.handle_match_request(event_data)

            mock_match.assert_called_once_with(
                "product_001",
                "video_001",
                "job_001",
            )

    @pytest.mark.asyncio
    async def test_handle_match_request_exception(
        self,
        matcher_service: MatcherService,
        mock_db: MagicMock,
    ) -> None:
        mock_db.fetch_all.side_effect = [
            [{"product_id": "product_001", "title": "Product 1"}],
            [{"video_id": "video_001", "title": "Video 1"}],
        ]

        with patch.object(
            matcher_service.matching_engine,
            "match_product_video",
            side_effect=Exception("Matching failed"),
        ) as mock_match:
            event_data = {
                "job_id": "job_001",
                "event_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
            }

            with pytest.raises(Exception, match="Matching failed"):
                await matcher_service.handle_match_request(event_data)

            mock_match.assert_called_once_with(
                "product_001",
                "video_001",
                "job_001",
            )
