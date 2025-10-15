"""Expanded unit tests for embedding_similarity module."""

from unittest.mock import patch

import numpy as np
import pytest

from utils.embedding_similarity import EmbeddingSimilarity


class TestEmbeddingSimilarityExpanded:
    """Expanded tests for EmbeddingSimilarity class."""

    def test_init_with_default_weights(self):
        """Test initialization with default weights."""
        sim = EmbeddingSimilarity()
        assert sim.weights == {"rgb": 0.7, "gray": 0.3}

    def test_init_with_custom_weights(self):
        """Test initialization with custom weights."""
        custom_weights = {"rgb": 0.8, "gray": 0.2}
        sim = EmbeddingSimilarity(custom_weights)
        assert sim.weights == custom_weights

    def test_init_weight_warning_logging(self):
        """Test that weight warning is logged when weights don't sum to 1.0."""
        bad_weights = {"rgb": 0.9, "gray": 0.2}  # Sum = 1.1

        with patch('utils.embedding_similarity.logger') as mock_logger:
            _ = EmbeddingSimilarity(bad_weights)
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args
            assert "Weights should sum to 1.0" in warning_call[0][0]
            assert warning_call[0][1] == 1.1  # The second argument should be the sum

    def test_init_weight_within_tolerance(self):
        """Test that weights within 0.01 tolerance don't trigger warning."""
        # Sum = 0.999, within 0.01 tolerance but won't trigger warning
        near_perfect_weights = {"rgb": 0.699, "gray": 0.3}

        with patch('utils.embedding_similarity.logger') as mock_logger:
            _ = EmbeddingSimilarity(near_perfect_weights)
            # The warning triggers when abs(sum - 1.0) > 0.01
            # For 0.999, abs(0.999 - 1.0) = 0.001 <= 0.01, so no warning
            mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_calculate_similarity_gray_only_inputs(self):
        """Test similarity calculation with only grayscale embeddings."""
        sim = EmbeddingSimilarity()

        image_embedding = {"emb_gray": np.array([0.1, 0.2, 0.3, 0.4, 0.5])}
        frame_embedding = {"emb_gray": np.array([0.1, 0.2, 0.3, 0.4, 0.5])}

        result = await sim.calculate_similarity(image_embedding, frame_embedding)

        assert result == pytest.approx(1.0)  # Identical vectors should have similarity 1.0

    @pytest.mark.asyncio
    async def test_calculate_similarity_rgb_only_inputs(self):
        """Test similarity calculation with only RGB embeddings."""
        sim = EmbeddingSimilarity()

        image_embedding = {"emb_rgb": np.array([0.1, 0.2, 0.3, 0.4, 0.5])}
        frame_embedding = {"emb_rgb": np.array([0.1, 0.2, 0.3, 0.4, 0.5])}

        result = await sim.calculate_similarity(image_embedding, frame_embedding)

        assert result == pytest.approx(1.0)  # Identical vectors should have similarity 1.0

    @pytest.mark.asyncio
    async def test_calculate_similarity_zero_norm_vectors(self):
        """Test similarity calculation with zero-norm vectors."""
        sim = EmbeddingSimilarity()

        # Create zero vectors
        zero_vec = np.zeros(5)
        image_embedding = {"emb_rgb": zero_vec}
        frame_embedding = {"emb_rgb": zero_vec}

        result = await sim.calculate_similarity(image_embedding, frame_embedding)

        assert result == 0.0  # Zero vectors should result in 0.0 similarity

    @pytest.mark.asyncio
    async def test_calculate_similarity_mixed_zero_norm(self):
        """Test with one zero vector and one non-zero vector."""
        sim = EmbeddingSimilarity()

        zero_vec = np.zeros(5)
        normal_vec = np.array([0.1, 0.2, 0.3, 0.4, 0.5])

        image_embedding = {"emb_rgb": zero_vec}
        frame_embedding = {"emb_rgb": normal_vec}

        result = await sim.calculate_similarity(image_embedding, frame_embedding)

        assert result == 0.0  # One zero vector should result in 0.0 similarity

    @pytest.mark.asyncio
    async def test_calculate_similarity_invalid_embeddings(self):
        """Test similarity calculation with invalid embeddings."""
        sim = EmbeddingSimilarity()

        # Missing both embeddings
        image_embedding = {}
        frame_embedding = {}

        with patch('utils.embedding_similarity.logger') as mock_logger:
            result = await sim.calculate_similarity(image_embedding, frame_embedding)

            assert result == 0.0
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args
            assert "Invalid embeddings provided" in warning_call[0][0]

    @pytest.mark.asyncio
    async def test_calculate_similarity_partial_embeddings(self):
        """Test with only one type of embedding present."""
        sim = EmbeddingSimilarity()

        # Image has RGB, frame has gray
        image_embedding = {"emb_rgb": np.array([0.1, 0.2, 0.3])}
        frame_embedding = {"emb_gray": np.array([0.1, 0.2, 0.3])}

        result = await sim.calculate_similarity(image_embedding, frame_embedding)

        assert result == 0.0  # Should return 0.0 when no matching embedding types

    def test_get_embedding_stats_empty_list(self):
        """Test get_embedding_stats with empty list."""
        sim = EmbeddingSimilarity()

        result = sim.get_embedding_stats([])

        assert result == {
            "count": 0,
            "rgb_self_similarity_mean": 0.0,
            "gray_self_similarity_mean": 0.0,
        }

    def test_get_embedding_stats_only_rgb(self):
        """Test get_embedding_stats with only RGB embeddings."""
        sim = EmbeddingSimilarity()

        # Create embeddings with only RGB (as lists to avoid numpy boolean issues)
        embeddings = [
            {"emb_rgb": [0.1, 0.2, 0.3], "emb_gray": None},
            {"emb_rgb": [0.4, 0.5, 0.6], "emb_gray": None},
        ]

        result = sim.get_embedding_stats(embeddings)

        assert result["count"] == 2
        assert result["rgb_self_similarity_mean"] == 0.0  # No embeddings with BOTH rgb and gray
        assert result["gray_self_similarity_mean"] == 0.0  # No embeddings with BOTH rgb and gray

    def test_get_embedding_stats_only_gray(self):
        """Test get_embedding_stats with only grayscale embeddings."""
        sim = EmbeddingSimilarity()

        embeddings = [
            {"emb_rgb": None, "emb_gray": [0.1, 0.2, 0.3]},
            {"emb_rgb": None, "emb_gray": [0.4, 0.5, 0.6]},
        ]

        result = sim.get_embedding_stats(embeddings)

        assert result["count"] == 2
        assert result["rgb_self_similarity_mean"] == 0.0  # No embeddings with BOTH rgb and gray
        assert result["gray_self_similarity_mean"] == 0.0  # No embeddings with BOTH rgb and gray

    def test_get_embedding_stats_mixed_embeddings(self):
        """Test get_embedding_stats with mixed RGB and grayscale embeddings."""
        sim = EmbeddingSimilarity()

        embeddings = [
            {"emb_rgb": [0.1, 0.2, 0.3], "emb_gray": [0.4, 0.5, 0.6]},
            {"emb_rgb": [0.7, 0.8, 0.9], "emb_gray": [0.1, 0.2, 0.3]},
        ]

        result = sim.get_embedding_stats(embeddings)

        assert result["count"] == 2
        assert result["rgb_self_similarity_mean"] == pytest.approx(1.0)
        assert result["gray_self_similarity_mean"] == pytest.approx(1.0)

    def test_get_embedding_stats_partial_embeddings(self):
        """Test get_embedding_stats with some embeddings missing types."""
        sim = EmbeddingSimilarity()

        # Mix: one with both, one with only RGB, one with only gray, one with neither
        embeddings = [
            {"emb_rgb": [0.1, 0.2, 0.3], "emb_gray": [0.4, 0.5, 0.6]},
            {"emb_rgb": [0.7, 0.8, 0.9], "emb_gray": None},
            {"emb_rgb": None, "emb_gray": [0.1, 0.2, 0.3]},
            {"emb_rgb": None, "emb_gray": None},
        ]

        result = sim.get_embedding_stats(embeddings)

        assert result["count"] == 4
        # Only the first embedding has both types, so it's the only one counted
        assert result["rgb_self_similarity_mean"] == pytest.approx(1.0)  # One embedding with both types
        assert result["gray_self_similarity_mean"] == pytest.approx(1.0)  # One embedding with both types

    @pytest.mark.asyncio
    async def test_calculate_similarity_negative_values(self):
        """Test similarity calculation with negative embedding values."""
        sim = EmbeddingSimilarity()

        # Vectors with negative values
        image_embedding = {"emb_rgb": np.array([-0.1, -0.2, -0.3])}
        frame_embedding = {"emb_rgb": np.array([-0.1, -0.2, -0.3])}

        result = await sim.calculate_similarity(image_embedding, frame_embedding)

        assert result == 1.0  # Identical vectors with negative values should still be 1.0

    @pytest.mark.asyncio
    async def test_calculate_similarity_clamping(self):
        """Test that similarity scores are properly clamped between 0 and 1."""
        sim = EmbeddingSimilarity()

        # Create vectors that would produce cosine similarity > 1 due to numerical precision
        image_embedding = {"emb_rgb": np.array([1.0, 0.0, 0.0])}
        frame_embedding = {"emb_rgb": np.array([1.0, 0.0, 0.0])}

        result = await sim.calculate_similarity(image_embedding, frame_embedding)

        assert 0.0 <= result <= 1.0
        assert result == 1.0

    @pytest.mark.asyncio
    async def test_calculate_similarity_exception_handling(self):
        """Test exception handling in calculate_similarity."""
        sim = EmbeddingSimilarity()

        # Create embeddings that will cause an exception in cosine similarity
        image_embedding = {"emb_rgb": "invalid"}
        frame_embedding = {"emb_rgb": np.array([0.1, 0.2, 0.3])}

        result = await sim.calculate_similarity(image_embedding, frame_embedding)

        assert result == 0.0  # Should return 0.0 on error

    def test_calculate_cosine_similarity_direct(self):
        """Test _calculate_cosine_similarity method directly."""
        sim = EmbeddingSimilarity()

        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])

        result = sim._calculate_cosine_similarity(vec1, vec2)

        assert result == 0.0  # Orthogonal vectors should have 0.0 similarity

    def test_calculate_cosine_similarity_orthogonal(self):
        """Test cosine similarity with orthogonal vectors."""
        sim = EmbeddingSimilarity()

        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])

        result = sim._calculate_cosine_similarity(vec1, vec2)

        assert pytest.approx(result, rel=1e-6) == 0.0

    def test_calculate_cosine_similarity_opposite_directions(self):
        """Test cosine similarity with vectors in opposite directions."""
        sim = EmbeddingSimilarity()

        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([-1.0, 0.0, 0.0])

        result = sim._calculate_cosine_similarity(vec1, vec2)

        assert pytest.approx(result, rel=1e-6) == 0.0  # Clamped to 0.0

    @pytest.mark.asyncio
    async def test_batch_similarity_search_empty_candidates(self):
        """Test batch_similarity_search with empty candidates."""
        sim = EmbeddingSimilarity()

        query_embedding = {"emb_rgb": np.array([0.1, 0.2, 0.3])}
        candidates = []

        result = await sim.batch_similarity_search(query_embedding, candidates)

        assert result == []

    @pytest.mark.asyncio
    async def test_batch_similarity_search_sorting(self):
        """Test that batch_similarity_search sorts by similarity."""
        sim = EmbeddingSimilarity()

        query_embedding = {"emb_rgb": np.array([1.0, 0.0, 0.0])}
        candidates = [
            {"frame_id": "f1", "emb_rgb": np.array([0.8, 0.2, 0.0])},  # Should be first
            {"frame_id": "f2", "emb_rgb": np.array([0.3, 0.7, 0.0])},  # Should be second
            {"frame_id": "f3", "emb_rgb": np.array([0.1, 0.9, 0.0])},  # Should be third
        ]

        result = await sim.batch_similarity_search(query_embedding, candidates, top_k=3)

        assert len(result) == 3
        assert result[0]["frame_id"] == "f1"
        assert result[1]["similarity"] >= result[2]["similarity"]

    @pytest.mark.asyncio
    async def test_batch_similarity_search_top_k_limiting(self):
        """Test that batch_similarity_search respects top_k parameter."""
        sim = EmbeddingSimilarity()

        query_embedding = {"emb_rgb": np.array([1.0, 0.0, 0.0])}
        candidates = [
            {"frame_id": "f1", "emb_rgb": np.array([0.8, 0.2, 0.0])},
            {"frame_id": "f2", "emb_rgb": np.array([0.7, 0.3, 0.0])},
            {"frame_id": "f3", "emb_rgb": np.array([0.6, 0.4, 0.0])},
            {"frame_id": "f4", "emb_rgb": np.array([0.5, 0.5, 0.0])},
        ]

        result = await sim.batch_similarity_search(query_embedding, candidates, top_k=2)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_batch_similarity_search_zero_similarity_filtering(self):
        """Test that zero similarity results are filtered out."""
        sim = EmbeddingSimilarity()

        query_embedding = {"emb_rgb": np.array([1.0, 0.0, 0.0])}
        candidates = [
            {"frame_id": "f1", "emb_rgb": np.array([1.0, 0.0, 0.0])},  # High similarity
            {"frame_id": "f2", "emb_rgb": np.array([0.0, 0.0, 0.0])},  # Zero similarity
            {"frame_id": "f3", "emb_rgb": np.array([0.8, 0.2, 0.0])},  # Medium similarity
        ]

        result = await sim.batch_similarity_search(query_embedding, candidates, top_k=10)

        # Should not include the zero similarity result
        frame_ids = [r["frame_id"] for r in result]
        assert "f2" not in frame_ids
        assert "f1" in frame_ids
        assert "f3" in frame_ids

    def test_get_embedding_stats_exception_handling(self):
        """Test exception handling in get_embedding_stats."""
        sim = EmbeddingSimilarity()

        # Create embeddings that will cause an exception
        embeddings = [
            {"emb_rgb": "invalid", "emb_gray": np.array([0.1, 0.2, 0.3])},
        ]

        result = sim.get_embedding_stats(embeddings)

        # Should return default values on error
        assert result == {
            "count": 0,
            "rgb_self_similarity_mean": 0.0,
            "gray_self_similarity_mean": 0.0,
        }
