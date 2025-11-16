"""Unit tests for CompletionEventPublisher - successful-only batch event counts."""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from vision_common.job_progress_manager.completion_event_publisher import CompletionEventPublisher
from vision_common import JobProgressManager


class TestCompletionEventPublisherSuccessOnly:
    """Test CompletionEventPublisher emits correct batch counts for successful-only progress."""

    @pytest.fixture
    def mock_broker(self):
        """Mock message broker."""
        broker = AsyncMock()
        broker.publish_event = AsyncMock()
        return broker

    @pytest.fixture
    def mock_base_manager(self):
        """Mock base manager with job tracking."""
        manager = MagicMock()
        manager.job_tracking = {}
        manager.job_image_counts = {}
        manager.job_frame_counts = {}
        return manager

    @pytest.fixture
    def publisher(self, mock_broker, mock_base_manager):
        """Create CompletionEventPublisher instance."""
        return CompletionEventPublisher(mock_broker, mock_base_manager)

    @pytest.mark.asyncio
    async def test_products_images_masked_batch_uses_successful_count(self, publisher, mock_broker, mock_base_manager):
        """Test that products.images.masked.batch event uses successful-only count."""
        # Arrange
        job_id = "image_success_job"
        total_expected = 5
        successful_count = 3  # Only 3 out of 5 succeeded

        # Mock job tracking to reflect successful-only progress
        mock_base_manager.job_tracking = {
            f"{job_id}:image:segmentation": {
                "done": successful_count,  # This should be successful-only
                "expected": total_expected
            }
        }

        # Mock event data
        event_id = str(uuid.uuid4())
        expected_event_data = {
            "event_id": event_id,
            "job_id": job_id,
            "total_images": successful_count  # Should be successful count, not expected
        }

        # Act
        await publisher.publish_products_images_masked_batch(job_id, successful_count)

        # Assert
        mock_broker.publish_event.assert_called_once_with(
            topic="products.images.masked.batch",
            event_data=expected_event_data
        )

        # Verify completion key tracking
        completion_key = f"{job_id}:products.images.masked.batch"
        assert completion_key in publisher._completion_events_sent

    @pytest.mark.asyncio
    async def test_videos_keyframes_masked_batch_uses_successful_count(self, publisher, mock_broker, mock_base_manager):
        """Test that video.keyframes.masked.batch event uses successful-only count."""
        # Arrange
        job_id = "video_success_job"
        total_expected = 8
        successful_count = 5  # Only 5 out of 8 succeeded

        # Mock job tracking to reflect successful-only progress
        mock_base_manager.job_tracking = {
            f"{job_id}:video:segmentation": {
                "done": successful_count,  # This should be successful-only
                "expected": total_expected
            }
        }

        # Mock event data
        event_id = str(uuid.uuid4())
        expected_event_data = {
            "event_id": event_id,
            "job_id": job_id,
            "total_keyframes": successful_count  # Should be successful count, not expected
        }

        # Act
        await publisher.publish_videos_keyframes_masked_batch(job_id, successful_count)

        # Assert
        mock_broker.publish_event.assert_called_once_with(
            topic="video.keyframes.masked.batch",
            event_data=expected_event_data
        )

        # Verify completion key tracking
        completion_key = f"{job_id}:video.keyframes.masked.batch"
        assert completion_key in publisher._completion_events_sent

    @pytest.mark.asyncio
    async def test_completion_event_emission_with_partial_success(self, publisher, mock_broker, mock_base_manager):
        """Test completion event emission with partial success scenarios."""
        # Test both image and video scenarios with partial success
        test_scenarios = [
            {
                "job_id": "partial_image_job",
                "asset_type": "image",
                "expected": 10,
                "done": 6,  # 6 successful out of 10 expected
                "should_be_partial": True
            },
            {
                "job_id": "partial_video_job",
                "asset_type": "video",
                "expected": 15,
                "done": 8,  # 8 successful out of 15 expected
                "should_be_partial": True
            },
            {
                "job_id": "full_success_job",
                "asset_type": "image",
                "expected": 5,
                "done": 5,  # All 5 successful
                "should_be_partial": False
            }
        ]

        for scenario in test_scenarios:
            # Reset mocks
            mock_broker.reset_mock()
            publisher._completion_events_sent.clear()

            # Arrange
            job_id = scenario["job_id"]
            asset_type = scenario["asset_type"]
            expected = scenario["expected"]
            done = scenario["done"]
            has_partial = scenario["should_be_partial"]

            # Mock job tracking
            mock_base_manager.job_tracking = {
                f"{job_id}:{asset_type}:segmentation": {
                    "done": done,
                    "expected": expected
                }
            }

            # Act
            await publisher.publish_completion_event_with_count(
                job_id=job_id,
                asset_type=asset_type,
                expected=expected,
                done=done,
                event_type_prefix="segmentation"
            )

            # Assert
            expected_event_type = f"{asset_type}.segmentation.completed"
            mock_broker.publish_event.assert_called_once()

            call_args = mock_broker.publish_event.call_args
            assert call_args[0][0] == expected_event_type  # topic

            event_data = call_args[0][1]  # event_data
            assert event_data["job_id"] == job_id
            assert event_data["total_assets"] == expected  # Should show original expected
            assert event_data["processed_assets"] == done   # Should show successful-only count
            assert event_data["has_partial_completion"] == has_partial
            assert event_data["failed_assets"] == 0
            assert event_data["idempotent"] is True

    @pytest.mark.asyncio
    async def test_emit_segmentation_masked_batch_events_routes_correctly(self, publisher, mock_broker, mock_base_manager):
        """Test that emit_segmentation_masked_batch_events routes to correct batch event publishers."""
        # Test both image and video routing
        test_cases = [
            {
                "asset_type": "image",
                "job_id": "image_batch_test",
                "expected": 7,
                "done": 5,
                "expected_topic": "products.images.masked.batch",
                "expected_total_key": "total_images"
            },
            {
                "asset_type": "video",
                "job_id": "video_batch_test",
                "expected": 12,
                "done": 9,
                "expected_topic": "video.keyframes.masked.batch",
                "expected_total_key": "total_keyframes"
            }
        ]

        for case in test_cases:
            # Reset mocks
            mock_broker.reset_mock()
            publisher._completion_events_sent.clear()

            # Act
            await publisher.emit_segmentation_masked_batch_events(
                case["job_id"],
                case["asset_type"],
                case["expected"],
                case["done"]
            )

            # Assert
            mock_broker.publish_event.assert_called_once()

            call_args = mock_broker.publish_event.call_args
            assert call_args[0][0] == case["expected_topic"]

            event_data = call_args[0][1]
            assert event_data["job_id"] == case["job_id"]
            assert event_data[case["expected_total_key"]] == case["done"]  # Should be successful count

    @pytest.mark.asyncio
    async def test_duplicate_batch_event_prevention(self, publisher, mock_broker, mock_base_manager):
        """Test that duplicate batch events are prevented."""
        # Arrange
        job_id = "duplicate_test_job"
        successful_count = 4

        # Act - first call should succeed
        await publisher.publish_products_images_masked_batch(job_id, successful_count)
        first_call_count = mock_broker.publish_event.call_count

        # Act - second call should be prevented
        await publisher.publish_products_images_masked_batch(job_id, successful_count)
        second_call_count = mock_broker.publish_event.call_count

        # Assert - only one call should have been made
        assert first_call_count == 1
        assert second_call_count == 1  # Should not have increased

        # Verify completion key is tracked
        completion_key = f"{job_id}:products.images.masked.batch"
        assert completion_key in publisher._completion_events_sent

    @pytest.mark.asyncio
    async def test_zero_successful_assets_handling(self, publisher, mock_broker, mock_base_manager):
        """Test handling of zero successful assets (all failed)."""
        # Arrange
        job_id = "all_failed_job"
        total_expected = 5
        successful_count = 0  # All failed

        # Act
        await publisher.publish_products_images_masked_batch(job_id, successful_count)

        # Assert
        mock_broker.publish_event.assert_called_once()

        call_args = mock_broker.publish_event.call_args
        assert call_args[0][0] == "products.images.masked.batch"

        event_data = call_args[0][1]
        assert event_data["job_id"] == job_id
        assert event_data["total_images"] == 0  # Should be zero successful
        assert "event_id" in event_data
        assert event_data["event_id"] is not None