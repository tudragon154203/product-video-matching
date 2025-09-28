"""Unit tests for the matching engine orchestration."""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from matching import MatchingEngine

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_db() -> MagicMock:
    """Create a mock database manager."""

    db = MagicMock()
    db.fetch_all = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def sample_image() -> Dict[str, Any]:
    """Return a representative product image payload."""

    return {
        "img_id": "img_001",
        "local_path": "/data/products/img_001.jpg",
        "emb_rgb": [0.1, 0.2, 0.3, 0.4, 0.5],
        "emb_gray": [0.2, 0.3, 0.4, 0.5, 0.6],
        "kp_blob_path": "/data/keypoints/img_001.pkl",
    }


@pytest.fixture
def sample_video_frames() -> List[Dict[str, Any]]:
    """Return a short collection of video frames."""

    return [
        {
            "frame_id": "frame_001",
            "ts": 1.0,
            "local_path": "/data/videos/video1/frame_001.jpg",
            "emb_rgb": [0.1, 0.2, 0.3, 0.4, 0.5],
            "emb_gray": [0.2, 0.3, 0.4, 0.5, 0.6],
            "kp_blob_path": "/data/keypoints/frame_001.pkl",
        },
        {
            "frame_id": "frame_002",
            "ts": 2.0,
            "local_path": "/data/videos/video1/frame_002.jpg",
            "emb_rgb": [0.6, 0.7, 0.8, 0.9, 1.0],
            "emb_gray": [0.7, 0.8, 0.9, 1.0, 1.1],
            "kp_blob_path": "/data/keypoints/frame_002.pkl",
        },
    ]


@pytest.fixture
def matching_engine(mock_db: MagicMock) -> MatchingEngine:
    """Provide a matching engine instance wired to the mock database."""

    return MatchingEngine(mock_db, "/data", retrieval_topk=10)


class TestMatchingEngine:
    """Behavioural checks for the matching engine."""

    @pytest.mark.asyncio
    async def test_initialize(self, matching_engine: MatchingEngine) -> None:
        await matching_engine.initialize()

        assert matching_engine.retrieval_topk == 10
        assert matching_engine.sim_deep_min == 0.82

    @pytest.mark.asyncio
    async def test_cleanup(self, matching_engine: MatchingEngine) -> None:
        await matching_engine.cleanup()

    @pytest.mark.asyncio
    async def test_get_product_images(
        self,
        matching_engine: MatchingEngine,
        mock_db: MagicMock,
    ) -> None:
        mock_db.fetch_all.return_value = [
            {
                "img_id": "img_001",
                "local_path": "/path1.jpg",
                "emb_rgb": [0.1, 0.2],
            },
            {
                "img_id": "img_002",
                "local_path": "/path2.jpg",
                "emb_rgb": [0.3, 0.4],
            },
        ]

        images = await matching_engine.get_product_images("product_001")

        mock_db.fetch_all.assert_called_once()
        args, _ = mock_db.fetch_all.call_args
        query = args[0]
        assert "product_images" in query
        assert "WHERE product_id = $1" in query
        assert "emb_rgb IS NOT NULL" in query
        assert args[1] == "product_001"
        assert len(images) == 2

    @pytest.mark.asyncio
    async def test_get_video_frames(
        self,
        matching_engine: MatchingEngine,
        mock_db: MagicMock,
    ) -> None:
        mock_db.fetch_all.return_value = [
            {
                "frame_id": "frame_001",
                "ts": 1.0,
                "local_path": "/path1.jpg",
                "emb_rgb": [0.1, 0.2],
            },
            {
                "frame_id": "frame_002",
                "ts": 2.0,
                "local_path": "/path2.jpg",
                "emb_rgb": [0.3, 0.4],
            },
        ]

        frames = await matching_engine.get_video_frames("video_001")

        mock_db.fetch_all.assert_called_once()
        args, _ = mock_db.fetch_all.call_args
        query = args[0]
        assert "video_frames" in query
        assert "WHERE video_id = $1" in query
        assert "emb_rgb IS NOT NULL" in query
        assert "ORDER BY ts" in query
        assert args[1] == "video_001"
        assert len(frames) == 2

    @pytest.mark.asyncio
    async def test_retrieve_similar_frames_no_embedding(
        self,
        matching_engine: MatchingEngine,
        sample_image: Dict[str, Any],
        sample_video_frames: List[Dict[str, Any]],
    ) -> None:
        sample_image["emb_rgb"] = None

        similar_frames = await matching_engine.retrieve_similar_frames(
            sample_image,
            sample_video_frames,
        )

        assert len(similar_frames) == min(10, len(sample_video_frames))
        assert similar_frames[0]["frame_id"] == "frame_001"

    @pytest.mark.asyncio
    async def test_retrieve_similar_frames_with_embedding(
        self,
        matching_engine: MatchingEngine,
        sample_image: Dict[str, Any],
        sample_video_frames: List[Dict[str, Any]],
    ) -> None:
        with patch.object(
            matching_engine,
            "_vector_similarity_search",
            return_value=[
                {"frame_id": "frame_001", "similarity": 0.95},
                {"frame_id": "frame_002", "similarity": 0.85},
            ],
        ) as mock_vector_search:
            similar_frames = await matching_engine.retrieve_similar_frames(
                sample_image,
                sample_video_frames,
            )

            mock_vector_search.assert_called_once()
            assert len(similar_frames) == 2

    @pytest.mark.asyncio
    async def test_vector_similarity_search_success(
        self,
        matching_engine: MatchingEngine,
        sample_image: Dict[str, Any],
        sample_video_frames: List[Dict[str, Any]],
    ) -> None:
        matching_engine.db.execute = AsyncMock()
        matching_engine.db.fetch_all = AsyncMock(
            return_value=[
                {"frame_id": "frame_001", "similarity": 0.95},
                {"frame_id": "frame_002", "similarity": 0.85},
            ]
        )

        image_emb = np.array(sample_image["emb_rgb"], dtype=np.float32)
        similar_frames = await matching_engine._vector_similarity_search(
            image_emb,
            sample_video_frames,
        )

        matching_engine.db.fetch_all.assert_called_once()
        assert len(similar_frames) == 2

    @pytest.mark.asyncio
    async def test_vector_similarity_search_fallback(
        self,
        matching_engine: MatchingEngine,
        sample_image: Dict[str, Any],
        sample_video_frames: List[Dict[str, Any]],
    ) -> None:
        matching_engine.db.execute = AsyncMock()
        matching_engine.db.fetch_all = AsyncMock(
            side_effect=Exception("db error"),
        )

        image_emb = np.array(sample_image["emb_rgb"], dtype=np.float32)
        similar_frames = await matching_engine._vector_similarity_search(
            image_emb,
            sample_video_frames,
        )

        assert len(similar_frames) == 2
        assert "similarity" in similar_frames[0]

    @pytest.mark.asyncio
    async def test_fallback_similarity_search(
        self,
        matching_engine: MatchingEngine,
        sample_image: Dict[str, Any],
        sample_video_frames: List[Dict[str, Any]],
    ) -> None:
        similar_frames = await matching_engine._fallback_similarity_search(
            sample_image,
            sample_video_frames,
        )

        assert len(similar_frames) == 2
        assert "similarity" in similar_frames[0]

    @pytest.mark.asyncio
    async def test_calculate_embedding_similarity(
        self,
        matching_engine: MatchingEngine,
        sample_image: Dict[str, Any],
        sample_video_frames: List[Dict[str, Any]],
    ) -> None:
        similarity = await matching_engine.calculate_embedding_similarity(
            sample_image,
            sample_video_frames[0],
        )

        assert 0.0 <= similarity <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_embedding_similarity_no_embeddings(
        self,
        matching_engine: MatchingEngine,
        sample_image: Dict[str, Any],
        sample_video_frames: List[Dict[str, Any]],
    ) -> None:
        sample_image["emb_rgb"] = None
        sample_video_frames[0]["emb_rgb"] = None

        similarity = await matching_engine.calculate_embedding_similarity(
            sample_image,
            sample_video_frames[0],
        )

        assert 0.7 <= similarity <= 0.9

    @pytest.mark.asyncio
    async def test_calculate_keypoint_similarity(
        self,
        matching_engine: MatchingEngine,
        sample_image: Dict[str, Any],
        sample_video_frames: List[Dict[str, Any]],
    ) -> None:
        similarity = await matching_engine.calculate_keypoint_similarity(
            sample_image,
            sample_video_frames[0],
        )

        assert 0.0 <= similarity <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_keypoint_similarity_no_keypoints(
        self,
        matching_engine: MatchingEngine,
        sample_image: Dict[str, Any],
        sample_video_frames: List[Dict[str, Any]],
    ) -> None:
        sample_image["kp_blob_path"] = None
        sample_video_frames[0]["kp_blob_path"] = None

        similarity = await matching_engine.calculate_keypoint_similarity(
            sample_image,
            sample_video_frames[0],
        )

        assert 0.3 <= similarity <= 0.7

    @pytest.mark.asyncio
    async def test_calculate_pair_score(
        self,
        matching_engine: MatchingEngine,
        sample_image: Dict[str, Any],
        sample_video_frames: List[Dict[str, Any]],
    ) -> None:
        with patch.object(
            matching_engine,
            "calculate_embedding_similarity",
            return_value=0.8,
        ) as mock_emb, patch.object(
            matching_engine,
            "calculate_keypoint_similarity",
            return_value=0.7,
        ) as mock_kp:
            score = await matching_engine.calculate_pair_score(
                sample_image,
                sample_video_frames[0],
            )

            mock_emb.assert_called_once()
            mock_kp.assert_called_once()
            assert 0.0 <= score <= 1.0
