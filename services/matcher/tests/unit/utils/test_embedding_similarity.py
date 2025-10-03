"""Tests for :mod:`utils.embedding_similarity`."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import pytest

from utils.embedding_similarity import EmbeddingSimilarity

pytestmark = pytest.mark.unit


@pytest.fixture
def similarity() -> EmbeddingSimilarity:
    """Provide an :class:`EmbeddingSimilarity` instance for testing."""

    return EmbeddingSimilarity()


@pytest.fixture
def query_embedding() -> Dict[str, Any]:
    """Return a representative embedding used across tests."""

    return {
        "frame_id": "query",
        "emb_rgb": [1.0, 0.0, 0.0],
        "emb_gray": [0.0, 1.0, 0.0],
    }


def test_calculate_similarity_combines_rgb_and_gray(
    similarity: EmbeddingSimilarity,
    query_embedding: Dict[str, Any],
) -> None:
    """The similarity score blends RGB and grayscale components."""

    candidate_embedding = {
        "frame_id": "candidate",
        "emb_rgb": [1.0, 0.0, 0.0],
        "emb_gray": [0.0, 1.0, 0.0],
    }

    score = asyncio.run(
        similarity.calculate_similarity(query_embedding, candidate_embedding)
    )

    assert score == pytest.approx(1.0)


def test_calculate_similarity_uses_available_channel(
    similarity: EmbeddingSimilarity,
    query_embedding: Dict[str, Any],
) -> None:
    """The calculator falls back to grayscale embeddings when RGB is absent."""

    query = {"emb_gray": [1.0, 0.0]}
    candidate = {"emb_gray": [1.0, 0.0]}

    score = asyncio.run(similarity.calculate_similarity(query, candidate))

    assert score == pytest.approx(1.0)


def test_calculate_similarity_returns_zero_for_invalid_input(
    similarity: EmbeddingSimilarity,
) -> None:
    """Invalid embeddings are handled defensively and produce a score of ``0``."""

    score = asyncio.run(similarity.calculate_similarity({}, {}))

    assert score == 0.0


def test_batch_similarity_search_filters_and_sorts_results(
    similarity: EmbeddingSimilarity,
    query_embedding: Dict[str, Any],
) -> None:
    """Batch search keeps only positive similarities and returns them sorted."""

    candidate_embeddings: List[Dict[str, Any]] = [
        {
            "frame_id": "high",
            "emb_rgb": [1.0, 0.0, 0.0],
            "emb_gray": [0.0, 1.0, 0.0],
        },
        {
            "frame_id": "medium",
            "emb_rgb": [0.5, 0.5, 0.0],
            "emb_gray": [0.5, 0.5, 0.0],
        },
        {
            "frame_id": "zero",
            "emb_rgb": [0.0, 0.0, 1.0],
            "emb_gray": [0.0, 0.0, 1.0],
        },
    ]

    results = asyncio.run(
        similarity.batch_similarity_search(
            query_embedding,
            candidate_embeddings,
            top_k=2,
        )
    )

    assert [result["frame_id"] for result in results] == ["high", "medium"]
    assert all(result["similarity"] > 0 for result in results)


def test_get_embedding_stats_returns_means(similarity: EmbeddingSimilarity) -> None:
    """The statistics helper summarises the provided embeddings."""

    embeddings = [
        {
            "emb_rgb": [1.0, 0.0],
            "emb_gray": [0.5, 0.5],
        },
        {
            "emb_rgb": [0.0, 1.0],
            "emb_gray": [0.5, -0.5],
        },
    ]

    stats = similarity.get_embedding_stats(embeddings)

    assert stats["count"] == 2
    assert stats["rgb_self_similarity_mean"] == pytest.approx(1.0)
    assert stats["gray_self_similarity_mean"] == pytest.approx(1.0)
