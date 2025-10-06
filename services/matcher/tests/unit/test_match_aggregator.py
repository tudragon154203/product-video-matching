"""Unit tests for match_aggregator module."""

from unittest.mock import patch

import pytest

from matching_components.match_aggregator import MatchAggregator


class TestMatchAggregator:
    """Test the MatchAggregator class."""

    def test_init(self):
        """Test MatchAggregator initialization."""
        aggregator = MatchAggregator(
            match_best_min=0.90,
            match_cons_min=3,
            match_accept=0.85
        )

        assert aggregator.match_best_min == 0.90
        assert aggregator.match_cons_min == 3
        assert aggregator.match_accept == 0.85

    @pytest.mark.asyncio
    async def test_aggregate_matches_empty_list(self):
        """Test aggregation with empty matches list."""
        aggregator = MatchAggregator(0.88, 2, 0.80)

        result = await aggregator.aggregate_matches([], "product1", "video1")

        assert result is None

    @pytest.mark.asyncio
    async def test_aggregate_matches_successful_acceptance(self):
        """Test successful aggregation with acceptance."""
        aggregator = MatchAggregator(0.88, 2, 0.80)

        matches = [
            {"img_id": "i1", "frame_id": "f1", "ts": 10.5, "pair_score": 0.92},
            {"img_id": "i1", "frame_id": "f2", "ts": 15.0, "pair_score": 0.85},
            {"img_id": "i2", "frame_id": "f3", "ts": 20.0, "pair_score": 0.83},
        ]

        result = await aggregator.aggregate_matches(matches, "product1", "video1")

        assert result is not None
        assert result["best_img_id"] == "i1"
        assert result["best_frame_id"] == "f1"
        assert result["ts"] == 10.5
        assert result["best_pair_score"] == 0.92
        assert result["consistency"] == 2  # Two matches >= 0.80
        assert result["total_pairs"] == 3

    @pytest.mark.asyncio
    async def test_aggregate_matches_rejected_by_acceptance_rules(self):
        """Test aggregation rejected by acceptance rules."""
        aggregator = MatchAggregator(0.90, 3, 0.80)

        # Low best score and low consistency
        matches = [
            {"img_id": "i1", "frame_id": "f1", "ts": 10.5, "pair_score": 0.85},
            {"img_id": "i1", "frame_id": "f2", "ts": 15.0, "pair_score": 0.82},
        ]

        result = await aggregator.aggregate_matches(matches, "product1", "video1")

        assert result is None

    @pytest.mark.asyncio
    async def test_aggregate_matches_rejected_by_final_threshold(self):
        """Test aggregation rejected by final acceptance threshold."""
        aggregator = MatchAggregator(0.88, 2, 0.95)  # High final threshold

        matches = [
            {"img_id": "i1", "frame_id": "f1", "ts": 10.5, "pair_score": 0.89},
            {"img_id": "i1", "frame_id": "f2", "ts": 15.0, "pair_score": 0.81},
        ]

        result = await aggregator.aggregate_matches(matches, "product1", "video1")

        assert result is None

    @pytest.mark.asyncio
    async def test_aggregate_matches_high_score_exception(self):
        """Test acceptance due to high score even with low consistency."""
        aggregator = MatchAggregator(0.90, 5, 0.80)

        # High best score (>= 0.92) should accept even with low consistency
        matches = [
            {"img_id": "i1", "frame_id": "f1", "ts": 10.5, "pair_score": 0.93},
            {"img_id": "i1", "frame_id": "f2", "ts": 15.0, "pair_score": 0.79},
        ]

        result = await aggregator.aggregate_matches(matches, "product1", "video1")

        assert result is not None
        assert result["best_pair_score"] == 0.93

    def test_apply_acceptance_rules_accept_standard(self):
        """Test _apply_acceptance_rules with standard acceptance criteria."""
        aggregator = MatchAggregator(0.88, 2, 0.80)

        # Should accept - meets both criteria
        result = aggregator._apply_acceptance_rules(
            best_score=0.90,
            consistency=3,
            product_id="product1",
            video_id="video1"
        )

        assert result is True

    def test_apply_acceptance_rules_reject_standard(self):
        """Test _apply_acceptance_rules rejection with low scores."""
        aggregator = MatchAggregator(0.88, 2, 0.80)

        # Should reject - fails both criteria
        result = aggregator._apply_acceptance_rules(
            best_score=0.85,
            consistency=1,
            product_id="product1",
            video_id="video1"
        )

        assert result is False

    def test_apply_acceptance_rules_accept_high_score(self):
        """Test _apply_acceptance_rules acceptance due to high score."""
        aggregator = MatchAggregator(0.88, 2, 0.80)

        # Should accept due to high score >= 0.92
        result = aggregator._apply_acceptance_rules(
            best_score=0.92,
            consistency=1,
            product_id="product1",
            video_id="video1"
        )

        assert result is True

    def test_apply_acceptance_rules_log_rejection(self):
        """Test that rejection is logged appropriately."""
        aggregator = MatchAggregator(0.88, 2, 0.80)

        with patch('matching_components.match_aggregator.logger') as mock_logger:
            result = aggregator._apply_acceptance_rules(
                best_score=0.85,
                consistency=1,
                product_id="product1",
                video_id="video1"
            )

            assert result is False
            mock_logger.info.assert_called_once()
            log_call = mock_logger.info.call_args
            assert "Match rejected by acceptance rules" in log_call[0][0]
            assert log_call[1]["product_id"] == "product1"
            assert log_call[1]["video_id"] == "video1"
            assert log_call[1]["best_score"] == 0.85
            assert log_call[1]["consistency"] == 1

    def test_calculate_final_score_basic(self):
        """Test _calculate_final_score with basic case."""
        aggregator = MatchAggregator(0.88, 2, 0.80)

        matches = [
            {"img_id": "i1", "frame_id": "f1", "pair_score": 0.90},
            {"img_id": "i1", "frame_id": "f2", "pair_score": 0.82},
        ]

        result = aggregator._calculate_final_score(
            best_score=0.90,
            consistency=2,
            best_matches=matches
        )

        # Should be best_score + consistency_boost (0.90 + 0.02)
        assert result == 0.92

    def test_calculate_final_score_with_distinct_images_boost(self):
        """Test _calculate_final_score with distinct images boost."""
        aggregator = MatchAggregator(0.88, 2, 0.80)

        matches = [
            {"img_id": "i1", "frame_id": "f1", "pair_score": 0.90},
            {"img_id": "i2", "frame_id": "f2", "pair_score": 0.82},  # Different image
        ]

        result = aggregator._calculate_final_score(
            best_score=0.90,
            consistency=2,
            best_matches=matches
        )

        # Should be best_score + consistency_boost + distinct_images_boost (0.90 + 0.02 + 0.02)
        assert result == 0.94

    def test_calculate_final_score_high_consistency_boost(self):
        """Test _calculate_final_score with high consistency boost."""
        aggregator = MatchAggregator(0.88, 2, 0.80)

        matches = [
            {"img_id": "i1", "frame_id": "f1", "pair_score": 0.90},
            {"img_id": "i1", "frame_id": "f2", "pair_score": 0.85},
            {"img_id": "i1", "frame_id": "f3", "pair_score": 0.82},
        ]

        result = aggregator._calculate_final_score(
            best_score=0.90,
            consistency=3,  # >= 3 should get boost
            best_matches=matches
        )

        # Should be best_score + consistency_boost (0.90 + 0.02)
        assert result == 0.92

    def test_calculate_final_score_no_boosts(self):
        """Test _calculate_final_score with no boosts."""
        aggregator = MatchAggregator(0.88, 2, 0.80)

        matches = [
            {"img_id": "i1", "frame_id": "f1", "pair_score": 0.90},
        ]

        result = aggregator._calculate_final_score(
            best_score=0.90,
            consistency=1,  # < 3, no boost
            best_matches=matches
        )

        # Should be just best_score, no boosts
        assert result == 0.90

    def test_calculate_final_score_all_boosts(self):
        """Test _calculate_final_score with all possible boosts."""
        aggregator = MatchAggregator(0.88, 2, 0.80)

        matches = [
            {"img_id": "i1", "frame_id": "f1", "pair_score": 0.90},
            {"img_id": "i2", "frame_id": "f2", "pair_score": 0.85},  # Different image
            {"img_id": "i1", "frame_id": "f3", "pair_score": 0.82},
        ]

        result = aggregator._calculate_final_score(
            best_score=0.90,
            consistency=3,  # >= 3, get boost
            best_matches=matches  # >= 2 distinct images, get boost
        )

        # Should be best_score + both boosts (0.90 + 0.02 + 0.02)
        assert result == 0.94

    def test_check_final_acceptance_threshold_accept(self):
        """Test _check_final_acceptance_threshold acceptance."""
        aggregator = MatchAggregator(0.88, 2, 0.80)

        result = aggregator._check_final_acceptance_threshold(
            final_score=0.85,
            product_id="product1",
            video_id="video1"
        )

        assert result is True

    def test_check_final_acceptance_threshold_reject(self):
        """Test _check_final_acceptance_threshold rejection."""
        aggregator = MatchAggregator(0.88, 2, 0.80)

        with patch('matching_components.match_aggregator.logger') as mock_logger:
            result = aggregator._check_final_acceptance_threshold(
                final_score=0.75,  # Below threshold
                product_id="product1",
                video_id="video1"
            )

            assert result is False
            mock_logger.info.assert_called_once()
            log_call = mock_logger.info.call_args
            assert "Match rejected by final threshold" in log_call[0][0]
            assert log_call[1]["product_id"] == "product1"
            assert log_call[1]["video_id"] == "video1"
            assert log_call[1]["final_score"] == 0.75

    def test_check_final_acceptance_threshold_exact_boundary(self):
        """Test _check_final_acceptance_threshold at exact boundary."""
        aggregator = MatchAggregator(0.88, 2, 0.80)

        result = aggregator._check_final_acceptance_threshold(
            final_score=0.80,  # Exactly at threshold
            product_id="product1",
            video_id="video1"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_aggregate_matches_exception_handling(self):
        """Test exception handling in aggregate_matches."""
        aggregator = MatchAggregator(0.88, 2, 0.80)

        matches = [
            {"img_id": "i1", "frame_id": "f1", "ts": 10.5, "pair_score": "invalid"},  # Invalid type
        ]

        result = await aggregator.aggregate_matches(matches, "product1", "video1")

        assert result is None

    @pytest.mark.asyncio
    async def test_aggregate_matches_score_capping(self):
        """Test that final score is capped at 1.0."""
        aggregator = MatchAggregator(0.88, 2, 0.80)

        matches = [
            {"img_id": "i1", "frame_id": "f1", "ts": 10.5, "pair_score": 0.98},
            {"img_id": "i2", "frame_id": "f2", "ts": 15.0, "pair_score": 0.90},
        ]

        # Mock _calculate_final_score to return a value > 1.0
        with patch.object(aggregator, '_calculate_final_score', return_value=1.05):
            result = await aggregator.aggregate_matches(matches, "product1", "video1")

            assert result is not None
            # Score should be capped at 1.0
            assert result["score"] == 1.0