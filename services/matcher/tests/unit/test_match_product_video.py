"""Unit tests for match_product_video function in matching module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from matching import MatchingEngine


class TestMatchProductVideo:
    """Test the match_product_video method."""

    @pytest.fixture
    def matching_engine(self):
        """Create a MatchingEngine instance with mocked dependencies."""
        mock_db = AsyncMock()
        params = {
            "retrieval_topk": 20,
            "sim_deep_min": 0.82,
            "inliers_min": 0.35,
            "match_best_min": 0.88,
            "match_cons_min": 2,
            "match_accept": 0.80,
        }
        engine = MatchingEngine(mock_db, "/data", **params)
        return engine

    @pytest.mark.asyncio
    async def test_match_product_video_missing_images(self, matching_engine):
        """Test when no product images are found."""
        matching_engine.get_product_images = AsyncMock(return_value=[])
        matching_engine.get_video_frames = AsyncMock(return_value=[{"frame_id": "f1"}])

        result = await matching_engine.match_product_video("product1", "video1", "job1")

        assert result is None
        matching_engine.get_product_images.assert_called_once_with("product1")
        matching_engine.get_video_frames.assert_not_called()

    @pytest.mark.asyncio
    async def test_match_product_video_missing_frames(self, matching_engine):
        """Test when no video frames are found."""
        matching_engine.get_product_images = AsyncMock(return_value=[{"img_id": "i1"}])
        matching_engine.get_video_frames = AsyncMock(return_value=[])

        result = await matching_engine.match_product_video("product1", "video1", "job1")

        assert result is None
        matching_engine.get_product_images.assert_called_once_with("product1")
        matching_engine.get_video_frames.assert_called_once_with("video1")

    @pytest.mark.asyncio
    async def test_match_product_video_no_matches_above_threshold(self, matching_engine):
        """Test when no matches meet the similarity threshold."""
        # Mock data
        product_images = [{"img_id": "i1", "emb_rgb": [1, 2, 3]}]
        video_frames = [{"frame_id": "f1", "ts": 10.5, "emb_rgb": [4, 5, 6]}]

        matching_engine.get_product_images = AsyncMock(return_value=product_images)
        matching_engine.get_video_frames = AsyncMock(return_value=video_frames)

        # Mock vector searcher to return frames, but pair scorer returns low scores
        matching_engine.vector_searcher.retrieve_similar_frames = AsyncMock(
            return_value=video_frames
        )
        matching_engine.pair_score_calculator.calculate_pair_score = AsyncMock(
            return_value=0.75  # Below sim_deep_min of 0.82
        )

        result = await matching_engine.match_product_video("product1", "video1", "job1")

        assert result is None

    @pytest.mark.asyncio
    async def test_match_product_video_successful_match_aggregation(self, matching_engine):
        """Test successful matching with aggregation."""
        # Mock data
        product_images = [{"img_id": "i1", "emb_rgb": [1, 2, 3]}]
        video_frames = [{"frame_id": "f1", "ts": 10.5, "emb_rgb": [4, 5, 6]}]

        matching_engine.get_product_images = AsyncMock(return_value=product_images)
        matching_engine.get_video_frames = AsyncMock(return_value=video_frames)

        # Mock successful matching
        matching_engine.vector_searcher.retrieve_similar_frames = AsyncMock(
            return_value=video_frames
        )
        matching_engine.pair_score_calculator.calculate_pair_score = AsyncMock(
            return_value=0.90  # Above sim_deep_min
        )

        # Mock aggregation result
        expected_aggregation = {
            "best_img_id": "i1",
            "best_frame_id": "f1",
            "ts": 10.5,
            "score": 0.90,
            "best_pair_score": 0.90,
            "consistency": 1,
            "total_pairs": 1,
        }
        matching_engine.match_aggregator.aggregate_matches = AsyncMock(
            return_value=expected_aggregation
        )

        result = await matching_engine.match_product_video("product1", "video1", "job1")

        assert result == expected_aggregation

    @pytest.mark.asyncio
    async def test_match_product_video_multiple_images_and_frames(self, matching_engine):
        """Test matching with multiple product images and video frames."""
        # Mock data
        product_images = [
            {"img_id": "i1", "emb_rgb": [1, 2, 3]},
            {"img_id": "i2", "emb_rgb": [4, 5, 6]}
        ]
        video_frames = [
            {"frame_id": "f1", "ts": 10.5, "emb_rgb": [7, 8, 9]},
            {"frame_id": "f2", "ts": 15.0, "emb_rgb": [10, 11, 12]}
        ]

        matching_engine.get_product_images = AsyncMock(return_value=product_images)
        matching_engine.get_video_frames = AsyncMock(return_value=video_frames)

        # Mock vector search and pair scoring
        matching_engine.vector_searcher.retrieve_similar_frames = AsyncMock(
            return_value=video_frames
        )
        matching_engine.pair_score_calculator.calculate_pair_score = AsyncMock(
            return_value=0.90
        )

        # Mock aggregation
        expected_aggregation = {
            "best_img_id": "i1",
            "best_frame_id": "f1",
            "ts": 10.5,
            "score": 0.90,
            "best_pair_score": 0.90,
            "consistency": 2,
            "total_pairs": 2,
        }
        matching_engine.match_aggregator.aggregate_matches = AsyncMock(
            return_value=expected_aggregation
        )

        result = await matching_engine.match_product_video("product1", "video1", "job1")

        assert result == expected_aggregation

        # Verify vector searcher was called for each image
        assert matching_engine.vector_searcher.retrieve_similar_frames.call_count == 2

        # Verify pair scorer was called for each image-frame combination
        assert matching_engine.pair_score_calculator.calculate_pair_score.call_count == 4

    @pytest.mark.asyncio
    async def test_match_product_video_exception_handling(self, matching_engine):
        """Test that exceptions are handled gracefully."""
        matching_engine.get_product_images = AsyncMock(side_effect=Exception("Database error"))

        result = await matching_engine.match_product_video("product1", "video1", "job1")

        assert result is None

    @pytest.mark.asyncio
    async def test_match_product_video_empty_best_matches_after_filtering(self, matching_engine):
        """Test when all matches are filtered out by threshold."""
        # Mock data
        product_images = [{"img_id": "i1", "emb_rgb": [1, 2, 3]}]
        video_frames = [{"frame_id": "f1", "ts": 10.5, "emb_rgb": [4, 5, 6]}]

        matching_engine.get_product_images = AsyncMock(return_value=product_images)
        matching_engine.get_video_frames = AsyncMock(return_value=video_frames)

        # Mock vector search returns frames, but pair scorer returns varying scores
        matching_engine.vector_searcher.retrieve_similar_frames = AsyncMock(
            return_value=video_frames
        )
        matching_engine.pair_score_calculator.calculate_pair_score = AsyncMock(
            return_value=0.75  # All below sim_deep_min
        )

        result = await matching_engine.match_product_video("product1", "video1", "job1")

        assert result is None
        matching_engine.match_aggregator.aggregate_matches.assert_not_called()

    @pytest.mark.asyncio
    async def test_match_product_video_aggregation_returns_none(self, matching_engine):
        """Test when aggregation returns None (match rejected)."""
        # Mock data
        product_images = [{"img_id": "i1", "emb_rgb": [1, 2, 3]}]
        video_frames = [{"frame_id": "f1", "ts": 10.5, "emb_rgb": [4, 5, 6]}]

        matching_engine.get_product_images = AsyncMock(return_value=product_images)
        matching_engine.get_video_frames = AsyncMock(return_value=video_frames)

        # Mock successful matching but aggregation rejects
        matching_engine.vector_searcher.retrieve_similar_frames = AsyncMock(
            return_value=video_frames
        )
        matching_engine.pair_score_calculator.calculate_pair_score = AsyncMock(
            return_value=0.90
        )
        matching_engine.match_aggregator.aggregate_matches = AsyncMock(return_value=None)

        result = await matching_engine.match_product_video("product1", "video1", "job1")

        assert result is None

    @pytest.mark.asyncio
    async def test_match_product_video_mixed_scores(self, matching_engine):
        """Test with mixed pair scores - some above, some below threshold."""
        # Mock data
        product_images = [{"img_id": "i1", "emb_rgb": [1, 2, 3]}]
        video_frames = [
            {"frame_id": "f1", "ts": 10.5, "emb_rgb": [4, 5, 6]},
            {"frame_id": "f2", "ts": 15.0, "emb_rgb": [7, 8, 9]}
        ]

        matching_engine.get_product_images = AsyncMock(return_value=product_images)
        matching_engine.get_video_frames = AsyncMock(return_value=video_frames)

        # Mock vector search and mixed pair scoring
        matching_engine.vector_searcher.retrieve_similar_frames = AsyncMock(
            return_value=video_frames
        )

        def score_scorer(image, frame):
            if frame["frame_id"] == "f1":
                return 0.90  # Above threshold
            else:
                return 0.75  # Below threshold

        matching_engine.pair_score_calculator.calculate_pair_score = AsyncMock(
            side_effect=score_scorer
        )

        # Mock aggregation for only the above-threshold match
        expected_aggregation = {
            "best_img_id": "i1",
            "best_frame_id": "f1",
            "ts": 10.5,
            "score": 0.90,
            "best_pair_score": 0.90,
            "consistency": 1,
            "total_pairs": 1,
        }
        matching_engine.match_aggregator.aggregate_matches = AsyncMock(
            return_value=expected_aggregation
        )

        result = await matching_engine.match_product_video("product1", "video1", "job1")

        assert result == expected_aggregation

        # Verify aggregation was called with only one match (above threshold)
        call_args = matching_engine.match_aggregator.aggregate_matches.call_args
        best_matches = call_args[0][0]
        assert len(best_matches) == 1
        assert best_matches[0]["frame_id"] == "f1"

    @pytest.mark.asyncio
    async def test_match_product_video_best_matches_structure(self, matching_engine):
        """Test that best_matches has the correct structure passed to aggregator."""
        # Mock data
        product_images = [{"img_id": "i1", "emb_rgb": [1, 2, 3]}]
        video_frames = [{"frame_id": "f1", "ts": 10.5, "emb_rgb": [4, 5, 6]}]

        matching_engine.get_product_images = AsyncMock(return_value=product_images)
        matching_engine.get_video_frames = AsyncMock(return_value=video_frames)

        matching_engine.vector_searcher.retrieve_similar_frames = AsyncMock(
            return_value=video_frames
        )
        matching_engine.pair_score_calculator.calculate_pair_score = AsyncMock(
            return_value=0.90
        )

        # Capture the structure passed to aggregation
        captured_matches = None
        def capture_aggregation(matches, product_id, video_id):
            nonlocal captured_matches
            captured_matches = matches
            return {"test": "result"}

        matching_engine.match_aggregator.aggregate_matches = AsyncMock(
            side_effect=capture_aggregation
        )

        await matching_engine.match_product_video("product1", "video1", "job1")

        # Verify structure
        assert captured_matches is not None
        assert len(captured_matches) == 1
        match = captured_matches[0]
        assert "img_id" in match
        assert "frame_id" in match
        assert "ts" in match
        assert "pair_score" in match
        assert match["img_id"] == "i1"
        assert match["frame_id"] == "f1"
        assert match["ts"] == 10.5
        assert match["pair_score"] == 0.90